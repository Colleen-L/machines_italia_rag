#!/usr/bin/env python3
"""
Machines Italia URL discovery + content change detection.

Outputs:

    data/discovered_urls.txt
        All currently discovered Machines Italia URLs.

    data/changed_urls.txt
        URLs that are new or whose page content has changed.

    data/page_hashes.json
        SHA-256 content hash for each successfully fetched page.
"""
import hashlib
import json
import sys
import time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

BASE = "https://machinesitalia.org"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(compatible; MachinesItaliaRAGBot/1.0)"
    )
}

SEED_PAGES = [
    "/events",
    "/news",
    "/event-archives",
] + [
    f"/event-archives?page={i}"
    for i in range(1, 11)
]

HASH_FILE = Path("data/page_hashes.json")
URL_FILE = Path("data/discovered_urls.txt")
CHANGED_FILE = Path("data/changed_urls.txt")

def find_links(html: str) -> set[str]:
    """
    Find Machines Italia event and news article URLs.
    """
    soup = BeautifulSoup(html, "html.parser")
    found = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        # Convert relative URLs to absolute URLs
        if href.startswith("/"):
            href = BASE + href
        # Individual event pages
        if href.startswith(BASE + "/event/"):
            found.add(href)
        # Individual news pages
        elif href.startswith(BASE + "/news-article/"):
            found.add(href)
    return found

def clean_content(html: str) -> str:
    """
    Remove non-content HTML before calculating the hash.

    Prevents changes to scripts/styles/navigation
    from incorrectly triggering re-ingestion.
    """
    soup = BeautifulSoup(html, "html.parser")
    for element in soup([
        "script",
        "style",
        "noscript",
        "svg",
    ]):
        element.decompose()
    text = soup.get_text(" ", strip=True)
    text = " ".join(text.split())
    return text

def calculate_hash(content: str) -> str:
    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def load_previous_hashes() -> dict[str, str]:
    """
    Load hashes from the previous discovery run.
    """
    if not HASH_FILE.exists():
        return {}
    try:
        with HASH_FILE.open(
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as e:
        print(
            f"Warning: could not read {HASH_FILE}: {e}",
            file=sys.stderr,
        )
    return {}


def main():
    # discover URLs
    all_urls = set()
    for path in SEED_PAGES:
        url = BASE + path
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=20,
            )
            if response.status_code != 200:
                print(
                    f"(skip {url}: "
                    f"status {response.status_code})",
                    file=sys.stderr,
                    flush=True,
                )
                continue
            links = find_links(response.text)
            print(
                f"{url} -> {len(links)} links",
                file=sys.stderr,
                flush=True,
            )
            all_urls.update(links)
        except Exception as e:
            print(
                f"(error on {url}: {e})",
                file=sys.stderr,
                flush=True,
            )
        time.sleep(1)
    print(
        f"Discovered {len(all_urls)} unique URLs",
        file=sys.stderr,
    )

    # load prev hashes
    previous_hashes = load_previous_hashes()
    current_hashes = {}
    changed_urls = []

    # fetch every page and compare content
    for index, url in enumerate(
        sorted(all_urls),
        start=1,
    ):
        print(
            f"[{index}/{len(all_urls)}] "
            f"Checking {url}",
            file=sys.stderr,
            flush=True,
        )
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=20,
            )
            if response.status_code != 200:
                print(
                    f"  skipped: HTTP "
                    f"{response.status_code}",
                    file=sys.stderr,
                )
                continue
            content = clean_content(
                response.text
            )
            new_hash = calculate_hash(
                content
            )
            current_hashes[url] = new_hash
            old_hash = previous_hashes.get(url)
            # new page discovered
            if old_hash is None:
                changed_urls.append(url)
                print(
                    "  NEW PAGE",
                    file=sys.stderr,
                )
            # existing page with new content
            elif old_hash != new_hash:
                changed_urls.append(url)
                print(
                    "  CONTENT CHANGED",
                    file=sys.stderr,
                )
            # page unchanged
            else:
                print(
                    "  unchanged",
                    file=sys.stderr,
                )
        except Exception as e:
            print(
                f"  error: {e}",
                file=sys.stderr,
            )

        time.sleep(0.5)

    # save discovered URLs
    URL_FILE.write_text(
        "\n".join(sorted(all_urls)) + "\n",
        encoding="utf-8",
    )
    CHANGED_FILE.write_text(
        "\n".join(sorted(changed_urls))
        + (
            "\n"
            if changed_urls
            else ""
        ),
        encoding="utf-8",
    )

    # save curr hashes
    HASH_FILE.write_text(
        json.dumps(
            current_hashes,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    # summary
    unchanged_count = (
        len(all_urls)
        - len(changed_urls)
    )
    print("Discovery summary", file=sys.stderr,)
    print("---",file=sys.stderr,)
    print(f"Total URLs: {len(all_urls)}",file=sys.stderr,)
    print(f"New/changed: {len(changed_urls)}",file=sys.stderr,)
    print(f"Unchanged: {unchanged_count}",file=sys.stderr,)

if __name__ == "__main__":
    main()