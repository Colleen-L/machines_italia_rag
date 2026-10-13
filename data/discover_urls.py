#!/usr/bin/env python3
"""
Machines Italia URL discovery + content change detection.

Outputs:
    data/discovered_urls.txt
        All URLs currently discovered.
    data/changed_urls.txt
        URLs that are new or whose page content changed.
    data/deleted_urls.txt
        URLs that were previously discovered but are no longer discovered.
    data/page_hashes.json
        SHA-256 hash of the latest successfully fetched page content.
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
DELETED_FILE = Path("data/deleted_urls.txt")

REQUEST_TIMEOUT = 20

SEED_DELAY = 1.0
PAGE_DELAY = 0.5

def fetch_page(url: str) -> requests.Response:
    """
    Fetch a page with a consistent user agent and timeout.
    """
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response

def find_links(html: str) -> set[str]:
    """
    Extract Machines Italia event and news URLs.
    """
    soup = BeautifulSoup(html, "html.parser")

    found = set()

    for a in soup.find_all("a", href=True):

        href = a["href"].strip()

        # Convert relative URLs to absolute
        if href.startswith("/"):
            href = BASE + href

        # Only keep supported content types
        if href.startswith(BASE + "/event/"):
            found.add(href)
        elif href.startswith(BASE + "/news-article/"):
            found.add(href)
    return found


def discover_urls() -> set[str]:
    all_urls = set()
    failed_seeds = []
    for path in SEED_PAGES:
        url = BASE + path
        print(f"Checking seed page: {url}",file=sys.stderr,flush=True,)

        try:
            response = fetch_page(url)
            links = find_links(response.text)
            print(f"  Found {len(links)} content links",file=sys.stderr,flush=True,)
            all_urls.update(links)
        except Exception as exc:
            print(f"{exc}", file=sys.stderr,flush=True,)
            failed_seeds.append(url)
        time.sleep(SEED_DELAY)

    if failed_seeds:
        print("",file=sys.stderr,)
        print("One or more discovery seed pages failed.",file=sys.stderr,)
        for url in failed_seeds:
            print(f"  Failed seed: {url}",file=sys.stderr,)
        sys.exit(1)
    print("",file=sys.stderr,)
    print(f"Discovered {len(all_urls)} unique URLs.",file=sys.stderr,)
    return all_urls

def clean_content(html: str) -> str:
    """
    Convert HTML into normalized text
    """
    soup = BeautifulSoup(
        html,
        "html.parser",
    )
    for element in soup([
        "script",
        "style",
        "noscript",
        "svg",
    ]):
        element.decompose()
    text = soup.get_text(" ",strip=True,)
    # Normalize whitespace
    text = " ".join(text.split())
    return text

def calculate_hash(content: str) -> str:
    """
    Calculate SHA-256 hash
    """
    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()

def load_previous_hashes() -> dict[str, str]:
    """
    Load URL -> content hash mapping
    """
    if not HASH_FILE.exists():
        return {}
    try:
        with HASH_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        print(
            f"Could not read {HASH_FILE}: {exc}",
            file=sys.stderr,
        )
    return {}


def load_previous_urls() -> set[str]:
    """
    Load the URL list from the previous successful discovery
    """
    if not URL_FILE.exists():
        return set()
    urls = set()
    with URL_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            url = line.strip()
            if url:
                urls.add(url)
    return urls

def write_url_file(
    path: Path,
    urls: set[str] | list[str],
) -> None:
    """
    Write sorted URLs, one per line
    """
    sorted_urls = sorted(urls)
    if sorted_urls:
        content = "\n".join(sorted_urls) + "\n"
    else:
        content = ""
    path.write_text(
        content,
        encoding="utf-8",
    )

def main():
    current_urls = discover_urls()
    previous_urls = load_previous_urls()
    previous_hashes = load_previous_hashes()

    print("",file=sys.stderr,)
    print(f"Previous URL count: {len(previous_urls)}",file=sys.stderr,)
    print(f"Current URL count:  {len(current_urls)}",file=sys.stderr,)

    deleted_urls = previous_urls - current_urls
    changed_urls = []
    current_hashes = {}
    sorted_current_urls = sorted(current_urls)

    print("",file=sys.stderr,)
    print("Checking page content...",file=sys.stderr,)

    for index, url in enumerate(
        sorted_current_urls,
        start=1,
    ):

        print(f"[{index}/{len(sorted_current_urls)}] {url}",file=sys.stderr,flush=True,)

        try:
            response = fetch_page(url)
            content = clean_content(
                response.text
            )
            new_hash = calculate_hash(
                content
            )
            current_hashes[url] = new_hash
            old_hash = previous_hashes.get(url)
            if old_hash is None:
                changed_urls.append(url)
                print(
                    "  -> NEW",
                    file=sys.stderr,
                )
            elif old_hash != new_hash:
                changed_urls.append(url)
                print("  -> CONTENT CHANGED",file=sys.stderr,)
            else:
                print("  -> unchanged",file=sys.stderr,)
        except Exception as exc:
            print(f"  -> ERROR: {exc}",file=sys.stderr,)
            if url in previous_hashes:
                current_hashes[url] = previous_hashes[url]

        time.sleep(PAGE_DELAY)

    # write current
    write_url_file(
        URL_FILE,
        current_urls,
    )
    # write changed
    write_url_file(
        CHANGED_FILE,
        changed_urls,
    )
    # write deleted
    write_url_file(
        DELETED_FILE,
        deleted_urls,
    )
    # write hashes
    HASH_FILE.write_text(
        json.dumps(
            current_hashes,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    unchanged_count = (len(current_urls) - len(changed_urls))
    print("Discovery summary", file=sys.stderr,)
    print("---", file=sys.stderr,)
    print(f"Current URLs:       {len(current_urls)}",file=sys.stderr,)
    print(f"New/changed URLs:   {len(changed_urls)}",file=sys.stderr,)
    print(f"Deleted URLs:       {len(deleted_urls)}",file=sys.stderr,)
    print(f"Unchanged URLs:     {unchanged_count}",file=sys.stderr,)
    print("---",file=sys.stderr,)
    if deleted_urls:
        print("",file=sys.stderr,)
        print("Deleted URLs:",file=sys.stderr,)
        for url in sorted(deleted_urls):
            print(f"  {url}",file=sys.stderr,)
    if changed_urls:
        print("",file=sys.stderr,)
        print("New/changed URLs:",file=sys.stderr,)
        for url in sorted(changed_urls):
            print(f"  {url}",file=sys.stderr,)

if __name__ == "__main__":
    main()