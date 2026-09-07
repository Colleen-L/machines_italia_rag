#!/usr/bin/env python3
"""
Embeds a test string with OpenAI and upserts it into Pinecone.
Requires: OPENAI_API_KEY, PINECONE_API_KEY env vars.

Usage:
    pip install requests --break-system-packages
    python3 02_test_embed_and_upsert.py
"""
import os
import sys
import requests

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
INDEX_NAME = "machines-italia"

if not OPENAI_API_KEY or not PINECONE_API_KEY:
    print("ERROR: export OPENAI_API_KEY and PINECONE_API_KEY first.")
    sys.exit(1)

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
    data = resp.json()
    if not data.get("status", {}).get("ready"):
        print("WARNING: index not marked ready yet, this may still fail.")
    return data["host"]

def main():
    print("1. Getting embedding from OpenAI...")
    text = "Machines Italia test document. Pinecone ingestion pipeline is working."
    vector = get_embedding(text)
    print(f"Got {len(vector)}-dimensional vector")

    print("2. Looking up Pinecone index host...")
    host = get_index_host()
    print(f"Index host: {host}")

    print("3. Upserting test vector into Pinecone...")
    resp = requests.post(
        f"https://{host}/vectors/upsert",
        headers={"Api-Key": PINECONE_API_KEY, "Content-Type": "application/json"},
        json={
            "namespace": "test",
            "vectors": [
                {
                    "id": "test:doc:0",
                    "values": vector,
                    "metadata": {
                        "text": text,
                        "content_type": "test",
                        "url": "https://example.com/test",
                    },
                }
            ],
        },
        timeout=30,
    )
    resp.raise_for_status()
    print(f"Upsert response: {resp.json()}")
    print("\nSuccess if {'upsertedCount': 1} above; embeddings + Pinecone both work.")


if __name__ == "__main__":
    main()
