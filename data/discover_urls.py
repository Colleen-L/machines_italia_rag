#!/usr/bin/env python3
"""
Discovers Machines Italia URLs by crawling known archive pages

"Content discovery" step - use it to build your 150-300 page batch

Usage:
    pip install requests beautifulsoup4 --break-system-packages
    python3 discover_urls.py > discovered_urls.txt
"""
import re
import sys
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MachinesItaliaRAGBot/1.0)"}
BASE = "https://machinesitalia.org"

# archive pages known to link out to individual content pages.
SEED_PAGES = [
    "/events",
    "/news",
    "/event-archives",
] + [f"/event-archives?page={i}" for i in range(1, 11)]


def find_links(html: str) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    found = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        # convert relative URLs to absolute URLs
        if href.startswith("/"):
            href = BASE + href
        # collect individual event/news pages
        if href.startswith(BASE + "/event/"):
            found.add(href)
        elif href.startswith(BASE + "/news-article/"):
            found.add(href)

    return found


def main():
    all_urls = set()
    for path in SEED_PAGES:
        url = BASE + path
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                print(f"  (skip {url}: status {resp.status_code})", file=sys.stderr, flush=True)
                continue
            links = find_links(resp.text)
            print(f"  {url} -> {len(links)} links", file=sys.stderr, flush=True)
            all_urls.update(links)
        except Exception as e:
            print(f"  (error on {url}: {e})", file=sys.stderr, flush=True)
        time.sleep(1)  # be polite

    print(f"# Discovered {len(all_urls)} unique URLs", file=sys.stderr, flush=True)
    for u in sorted(all_urls):
        print(u)


if __name__ == "__main__":
    main()
