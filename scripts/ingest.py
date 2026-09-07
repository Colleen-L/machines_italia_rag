#!/usr/bin/env python3
"""
End-to-end ingestion of one or more Machines Italia URLs:
plain HTTP scrape -> classify content_type -> chunk -> embed -> upsert to Pinecone

Scraping using requests + BeautifulSoup.
This is the reference implementation. To be inserted into an n8n Code node.

Usage:
    pip install requests beautifulsoup4 --break-system-packages
    python3 ingest.py urls.txt
    # urls.txt = one URL per line

Requires env vars: OPENAI_API_KEY, PINECONE_API_KEY
"""
import os
import re
import sys
import time
import hashlib
import datetime as dt
import requests
from bs4 import BeautifulSoup

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
INDEX_NAME = "machines-italia"
NAMESPACE = "prod"  # switch to "test" while experimenting
CHUNK_SIZE_CHARS = 3000
CHUNK_OVERLAP_CHARS = 300
REQUEST_DELAY_SECONDS = 1.0

SCRAPE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MachinesItaliaRAGBot/1.0; +https://example.com/bot)"
}

# 1 Scrape
def scrape(url: str) -> dict:
    resp = requests.get(url, headers=SCRAPE_HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    title = soup.title.string.strip() if soup.title and soup.title.string else url

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        tag.decompose()

    # prefer <main>/<article> if present to reduces nav/footer noise.
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text(separator="\n")
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    return {"markdown": text, "title": title}

# 2 Classify and Extract Metadata
def classify_content_type(url: str) -> str:
    if "/event" in url:
        return "event"
    if "/news" in url:
        return "news"
    if "/industr" in url:
        return "industry"
    if "/about" in url or "/company" in url:
        return "company"
    return "main_page"

DATE_PATTERN = re.compile(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b")
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
EVENT_DATE_PATTERN = re.compile(
    r"\b(\d{1,2})(?:/(\d{1,2}))?\s+([A-Za-z]{3,9})\s+(\d{4})\b"
)

def extract_dates(text: str) -> list[str]:
    """Extracts ISO dates from both formats seen on the real site:
    - numeric: 2026-09-14
    - Machines Italia event style: '14/19 Sep 2026' or '16 Sep 2026'
      (day, or day-range within one month, then month name, then year)
    Returns sorted dates. For event ranges, it gives [start_date, end_date]
    """
    found = set()

    for m in DATE_PATTERN.finditer(text):
        y, mo, d = m.groups()
        try:
            found.add(dt.date(int(y), int(mo), int(d)).isoformat())
        except ValueError:
            continue

    for m in EVENT_DATE_PATTERN.finditer(text):
        day1, day2, month_name, year = m.groups()
        month_num = MONTHS.get(month_name.lower()[:3])
        if not month_num:
            continue
        for day in filter(None, [day1, day2]):
            try:
                found.add(dt.date(int(year), month_num, int(day)).isoformat())
            except ValueError:
                continue

    return sorted(found)

def date_to_timestamp(date_string: str) -> int:
    """Convert YYYY-MM-DD to Unix timestamp in milliseconds."""
    date = dt.datetime.strptime(date_string, "%Y-%m-%d")
    date = date.replace(tzinfo=dt.timezone.utc)
    return int(date.timestamp() * 1000)

def extract_location_city(text: str) -> str | None:
    """Extract a city from common event-page location patterns."""
    patterns = [
        r"(?:location|venue|city)\s*[:\-]\s*([A-Za-zÀ-ÿ' -]{2,50})",
        r"(?:held in|takes place in|located in)\s+([A-Za-zÀ-ÿ' -]{2,50})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            city = match.group(1).strip()
            # Avoid capturing excessively long text.
            if len(city) <= 50:
                return city
    return None

def build_metadata(url: str, title: str, markdown: str) -> dict:
    content_type = classify_content_type(url)
    dates = extract_dates(markdown)

    metadata = {
        "url": url,
        "title": title,
        "content_type": content_type,
        "language": "en",
        "scraped_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }

    if content_type == "event" and dates:
        metadata["event_start_date"] = date_to_timestamp(dates[0])
        metadata["event_end_date"] = date_to_timestamp(dates[-1])
        location_city = extract_location_city(markdown)
        if location_city:
            metadata["location_city"] = location_city
    elif content_type == "news" and dates:
        metadata["published_date"] = date_to_timestamp(dates[0])

    return metadata

# 3 Chunk
def chunk_text(text: str, size=CHUNK_SIZE_CHARS, overlap=CHUNK_OVERLAP_CHARS) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

# 4 Embed
def embed(text: str) -> list[float]:
    resp = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={"model": "text-embedding-3-small", "input": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]

# 5 Upsert
_index_host_cache = None

def get_index_host() -> str:
    global _index_host_cache
    if _index_host_cache:
        return _index_host_cache
    resp = requests.get(
        f"https://api.pinecone.io/indexes/{INDEX_NAME}",
        headers={"Api-Key": PINECONE_API_KEY, "X-Pinecone-API-Version": "2024-10"},
        timeout=30,
    )
    resp.raise_for_status()
    _index_host_cache = resp.json()["host"]
    return _index_host_cache

def upsert_vectors(vectors: list[dict]):
    host = get_index_host()
    resp = requests.post(
        f"https://{host}/vectors/upsert",
        headers={"Api-Key": PINECONE_API_KEY, "Content-Type": "application/json"},
        json={"namespace": NAMESPACE, "vectors": vectors},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()

def slugify(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")[:80]


# MAIN PIPELINE
def ingest_url(url: str):
    print(f"\nIngesting: {url}")
    time.sleep(REQUEST_DELAY_SECONDS)
    page = scrape(url)
    markdown = page["markdown"]
    if not markdown.strip():
        print("  WARNING: empty content, skipping.")
        return

    content_hash = hashlib.sha256(markdown.encode()).hexdigest()
    metadata = build_metadata(url, page["title"], markdown)
    metadata["content_hash"] = content_hash
    print(f"  content_type={metadata['content_type']}  title={page['title'][:60]}")

    chunks = chunk_text(markdown)
    print(f"  {len(chunks)} chunk(s)")

    slug = slugify(url)
    vectors = []
    for i, chunk in enumerate(chunks):
        vector = embed(chunk)
        chunk_metadata = dict(metadata)
        chunk_metadata["chunk_index"] = i
        chunk_metadata["text"] = chunk
        vectors.append({
            "id": f"{metadata['content_type']}:{slug}:{i}",
            "values": vector,
            "metadata": chunk_metadata,
        })

    result = upsert_vectors(vectors)
    print(f"  Upserted: {result}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ingest.py urls.txt")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    for url in urls:
        try:
            ingest_url(url)
        except Exception as e:
            print(f"  ERROR ingesting {url}: {e}")

if __name__ == "__main__":
    main()
