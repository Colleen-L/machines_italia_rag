#!/usr/bin/env python3
"""
Embeds a question and queries Pinecone to confirm retrieval works end-to-end.
Requires: OPENAI_API_KEY, PINECONE_API_KEY env vars.
Run ingest.py (or 02_test_embed_and_upsert.py) first so there's something to find.

Usage:
    python3 03_test_query.py "Is the pipeline working?"                       # namespace=test
    python3 03_test_query.py "What events are coming up?" --namespace prod
    python3 03_test_query.py "What events are coming up?" --namespace prod \\
        --filter '{"content_type": {"$eq": "event"}, "event_start_date": {"$gte": "2026-09-07"}}'
"""
import os
import sys
import json
import argparse
import requests

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
INDEX_NAME = "machines-italia"

if not OPENAI_API_KEY or not PINECONE_API_KEY:
    print("ERROR: export OPENAI_API_KEY and PINECONE_API_KEY first.")
    sys.exit(1)

parser = argparse.ArgumentParser()
parser.add_argument("question")
parser.add_argument("--namespace", default="test", help="Pinecone namespace to query (default: test)")
parser.add_argument("--top-k", type=int, default=5)
parser.add_argument("--filter", default=None, help="JSON metadata filter, e.g. '{\"content_type\":{\"$eq\":\"event\"}}'")
args = parser.parse_args()

question = args.question
metadata_filter = json.loads(args.filter) if args.filter else None

def get_embedding(text: str) -> list[float]:
    resp = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={"model": "text-embedding-3-small", "input": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]

def get_index_host() -> str:
    resp = requests.get(
        f"https://api.pinecone.io/indexes/{INDEX_NAME}",
        headers={"Api-Key": PINECONE_API_KEY, "X-Pinecone-API-Version": "2024-10"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["host"]

def main():
    print(f"Question: {question}")
    print(f"Namespace: {args.namespace}")
    if metadata_filter:
        print(f"Filter: {json.dumps(metadata_filter)}")
    vector = get_embedding(question)
    host = get_index_host()
    body = {
        "namespace": args.namespace,
        "vector": vector,
        "topK": args.top_k,
        "includeMetadata": True,
    }
    if metadata_filter:
        body["filter"] = metadata_filter

    resp = requests.post(
        f"https://{host}/query",
        headers={"Api-Key": PINECONE_API_KEY, "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    matches = resp.json().get("matches", [])

    if not matches:
        print("\nNo matches found. Either nothing's been ingested into this")
        print("namespace yet, or the filter excluded everything.")
        return

    print(f"\nTop {len(matches)} matches:")
    for m in matches:
        meta = m["metadata"]
        date_info = ""
        if "event_start_date" in meta:
            date_info = f"  [event: {meta['event_start_date']} to {meta.get('event_end_date', '?')}]"
        elif "published_date" in meta:
            date_info = f"  [published: {meta['published_date']}]"
        print(f"score={m['score']:.4f}  type={meta.get('content_type')}{date_info}")
        print(f"url: {meta.get('url')}")
        print(f"text: {meta.get('text', '')[:150]}...")

if __name__ == "__main__":
    main()
