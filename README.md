# Transfer Investigation Agent

An internal ops tool that investigates stuck or failed payment transfers, reconstructs the transfer timeline, identifies the likely failure point, and returns a cited draft response for human review and approval.

---

## Purpose

When a transfer complaint arrives, this agent:

1. **Retrieves relevant process documentation** from an internal knowledge base using Cohere's embedding and retrieval APIs
2. **Reconstructs the transfer timeline** from the complaint details and retrieved process rules
3. **Identifies the likely failure point** — the specific step in the transfer process where something went wrong
4. **Drafts a professional client-facing response** with citations to the source documents that informed the conclusion

The draft is returned to a human operator for review and approval before any communication is sent to the client.

---

## Architecture

```
POST /ingest
  └── Reads .txt files from knowledge_base/docs/
  └── Chunks and embeds via Cohere
  └── Upserts into ChromaDB

POST /investigate
  └── Embeds complaint via Cohere
  └── Retrieves top-K chunks from ChromaDB
  └── Calls Cohere chat (RAG) with complaint + context
  └── Returns: timeline, failure point, draft response, citations
```

---

## Project Structure

```
transfer-investigation-agent/
  app/
    main.py          # FastAPI app — route definitions
    ingest.py        # Document ingestion pipeline
    query.py         # Investigation pipeline
    models.py        # Pydantic request/response models
  knowledge_base/
    docs/            # Drop .txt process documents here before ingesting
  tests/
    test_query.py    # Test stubs — implement as logic is added
  requirements.txt
  .env.example
```

---

## Setup

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd transfer-investigation-agent

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and add your Cohere API key

# 5. Add process documents
# Drop .txt files into knowledge_base/docs/

# 6. Run the app

# Via FastAPI CLI
fastapi dev app/main.py

# Via UVICORN
uvicorn app.main:app --reload
```

---

## API

### `POST /ingest`

Reads all `.txt` files from `knowledge_base/docs/`, chunks them, embeds them with Cohere, and loads them into ChromaDB. Run this once after adding or updating documents.

**Response**
```json
{
  "success": true,
  "documents_ingested": 42,
  "message": "Ingestion complete."
}
```

---

### `POST /investigate`

Accepts a transfer complaint and returns a structured investigation output.

**Request**
```json
{
  "complaint": "Customer reports transfer of $4,200 to account ending 8821 initiated on 2024-11-03 has not arrived after 5 business days."
}
```

**Response**
```json
{
  "timeline": "...",
  "failure_point": "...",
  "draft_response": "...",
  "citations": [
    {
      "document_name": "wire-transfer-sla.txt",
      "excerpt": "..."
    }
  ]
}
```

> **Important:** The `draft_response` field is for human review only. Do not send it to clients without operator approval.

---

## Development Status

- [x] Project scaffold and route definitions
- [ ] Document ingestion pipeline (`app/ingest.py`)
- [ ] Investigation query pipeline (`app/query.py`)
- [ ] Prompt engineering and response parsing
- [ ] Test implementation (`tests/test_query.py`)
- [ ] Error handling and logging
- [ ] Deployment configuration

---

## Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `chromadb` | Local vector store |
| `cohere` | Embeddings and RAG chat |
| `python-dotenv` | Environment variable loading |
| `pydantic` | Request/response validation |
