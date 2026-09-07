#!/usr/bin/env bash
# Creates the "machines-italia" Pinecone serverless index.
# Requires: PINECONE_API_KEY env var set.
# Usage: ./00_create_pinecone_index.sh

set -euo pipefail

if [[ -z "${PINECONE_API_KEY:-}" ]]; then
  echo "ERROR: export PINECONE_API_KEY first."
  exit 1
fi

INDEX_NAME="machines-italia"

echo "Creating Pinecone index '$INDEX_NAME' (dim=1536, cosine, aws/us-east-1)..."

curl -sS -X POST "https://api.pinecone.io/indexes" \
  -H "Api-Key: $PINECONE_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-Pinecone-API-Version: 2024-10" \
  -d '{
    "name": "'"$INDEX_NAME"'",
    "dimension": 1536,
    "metric": "cosine",
    "spec": {
      "serverless": {
        "cloud": "aws",
        "region": "us-east-1"
      }
    }
  }' | python3 -m json.tool
