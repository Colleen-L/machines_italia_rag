# Machines Italia AI/RAG Knowledge Assistant

## Stack
- **n8n** — workflow orchestration
- **Plain HTTP GET + HTML stripping** — website scraping (no third-party scraping API/key required)
- **OpenAI** — embeddings (`text-embedding-3-small`, 1536-dim) + LLM
- **Pinecone** — vector database (single index, metadata-filtered namespaces)
