#!/usr/bin/env python3
"""
Scrapes ONE Machines Italia page with a plain HTTP GET + BeautifulSoup
(no Firecrawl / no third-party scraping API required).

Usage:
    pip install requests beautifulsoup4 --break-system-packages
    python3 01_test_scrape.py "https://machinesitalia.org/some-page"
"""
import sys
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MachinesItaliaRAGBot/1.0; +https://example.com/bot)"
}


def scrape(url: str) -> dict:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    title = soup.title.string.strip() if soup.title and soup.title.string else url

    # remove elements/tags that are never useful content
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        tag.decompose()

    # prefer <main> or <article> if provided to cut nav/footer noise
    main = soup.find("main") or soup.find("article") or soup.body or soup

    # collapse excessive blank lines/whitespace
    text = main.get_text(separator="\n")
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()

    return {"title": title, "text": text}


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 01_test_scrape.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Fetching: {url}")
    result = scrape(url)

    print(f"\nTitle: {result['title']}")
    print(f"\nExtracted text ({len(result['text'])} chars), first 1000 shown:\n")
    print(result["text"][:1000])


if __name__ == "__main__":
    main()
