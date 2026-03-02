# Transfer Investigation Agent

An internal ops tool that investigates stuck or failed payment transfers at Wealthsimple. Given a free-text complaint, it retrieves relevant process documentation via Cohere RAG, reconstructs the transfer timeline, identifies the likely failure point, and returns a cited draft response for human review and approval.

The draft is never sent to clients automatically — a human operator must review and approve it first.

---

## Stack

| Layer | Technology |
|---|---|
| API | Python 3.11, FastAPI, Uvicorn |
| AI | Cohere Embed v3, Rerank v3, Command R+ |
| Vector store | ChromaDB (local persistence) |
| Frontend | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS |
| Testing | pytest, pytest-asyncio |

---

## Project Structure

```
transfer-investigation-agent/
├── app/
│   ├── main.py              # FastAPI routes + startup auto-ingest
│   ├── ingest.py            # Document ingestion pipeline
│   ├── query.py             # Investigation pipeline (RAG + LLM)
│   ├── models.py            # Pydantic request/response models
│   └── static/              # Built frontend (output of `npm run build`)
├── frontend/                # Next.js 14 (App Router) source
│   ├── app/
│   │   ├── layout.tsx       # Root layout (Tailwind, metadata)
│   │   ├── page.tsx         # Two-panel investigation workspace
│   │   └── api/             # Next.js route handlers (proxy to FastAPI)
│   ├── components/
│   │   ├── ComplaintQueue.tsx    # Left panel — 5 queued complaints
│   │   ├── ComplaintInput.tsx    # Controlled textarea + submit button
│   │   ├── WorkflowStepper.tsx   # 5-step horizontal progress tracker
│   │   ├── ResultsPanel.tsx      # Investigation results + urgency badge
│   │   ├── ConfidenceScore.tsx   # Confidence bar
│   │   └── SourcesList.tsx       # Cited sources list
│   ├── lib/
│   │   ├── api.ts           # All fetch calls (no fetch elsewhere)
│   │   └── types.ts         # TypeScript interfaces (mirrors models.py)
│   ├── next.config.mjs
│   ├── tailwind.config.ts
│   └── package.json
├── knowledge_base/
│   └── docs/                # Drop .txt process documents here
├── tests/
│   └── test_query.py
├── requirements.txt
├── render.yaml              # Render deployment blueprint
├── Procfile                 # Backup start command
└── .env.example
```

---

## Local Setup

### 1. Clone and enter the repo

```bash
git clone <repo-url>
cd transfer-investigation-agent
```

### 2. Create a Python virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your Cohere API key

```bash
cp .env.example .env
# Open .env and set COHERE_API_KEY=<your key>
```

### 5. Ingest the knowledge base

The knowledge base must be populated before `/investigate` will work.

```bash
python -m app.ingest              # incremental (skips existing chunks)
python -m app.ingest --overwrite  # wipe and rebuild from scratch
```

Documents are read from `knowledge_base/docs/`. Add or replace `.txt` files there and re-run ingestion to update the knowledge base.

### 6. Run the app

```bash
fastapi dev app/main.py
# or
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

---

## Frontend Development

The frontend is a Next.js 14 project in `frontend/`. During development, Next.js route handlers in `frontend/app/api/` proxy API calls to FastAPI, so you only need one browser tab.

```bash
# Terminal 1 — FastAPI backend
fastapi dev app/main.py          # http://localhost:8000

# Terminal 2 — Next.js dev server (with HMR)
cd frontend
npm install
npm run dev                      # http://localhost:3000  ← open this
```

To build the frontend for production (output goes to `app/static/`):

```bash
cd frontend && npm run build
```

`NEXT_STATIC=1` is set automatically by the build script. FastAPI serves `app/static/` at `/` when the directory exists.

---

## Running Tests

```bash
pytest tests/ -v
```

All tests mock Cohere and ChromaDB — no API key or live database required.

---

## Deployment on Render

### Prerequisites

- A [Render](https://render.com) account (free tier is sufficient for demo use)
- A Cohere API key

### Steps

1. Push this repo to GitHub or GitLab.

2. In the Render dashboard, click **New → Blueprint** and connect your repository. Render will detect `render.yaml` automatically and configure the service.

   Alternatively, create a **New Web Service** manually with:
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt && cd frontend && npm install && npm run build`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

3. In the service's **Environment** tab, add:
   - `COHERE_API_KEY` = your Cohere API key

4. Deploy. On first start, the app will automatically ingest the knowledge base (see [Startup Auto-Ingest](#startup-auto-ingest) below).

### Startup Auto-Ingest

On startup, `app/main.py` checks whether the ChromaDB collection is empty. If it is, it runs ingestion automatically before serving requests. This means the app is ready to use immediately after a cold start without any manual steps.

You can also trigger ingestion manually at any time by calling `POST /ingest`.

### Knowledge Base Persistence Limitation

> **Important:** ChromaDB uses local filesystem persistence (`./chroma_db/`). On Render's free tier, the filesystem is **ephemeral** — it resets on every deploy and after periods of inactivity.

This means the vector store is rebuilt automatically on each cold start via the startup auto-ingest described above. The rebuild takes 30–60 seconds depending on the size of your knowledge base.

For a production deployment where persistence matters, replace ChromaDB with a managed vector store:

| Option | Notes |
|---|---|
| [Chroma Cloud](https://www.trychroma.com/) | Managed ChromaDB — minimal code change |
| [Pinecone](https://www.pinecone.io/) | Fully managed, generous free tier |
| [Weaviate Cloud](https://weaviate.io/) | Open-source, managed option available |

---

## API Reference

### `GET /health`

Returns service status and the number of chunks currently in the knowledge base.

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "knowledge_base_size": 47
}
```

A `knowledge_base_size` of `0` means ingestion has not run yet (or the Chroma collection was reset). Call `POST /ingest` to populate it.

---

### `POST /ingest`

Reads all `.txt` files from `knowledge_base/docs/`, chunks them (~300 tokens, 50-token overlap), embeds them with Cohere Embed v3, and upserts into ChromaDB.

**The knowledge base must be ingested before `/investigate` will return meaningful results.**

```bash
# Incremental — skips chunks already present
curl -X POST http://localhost:8000/ingest

# Wipe and rebuild from scratch
curl -X POST "http://localhost:8000/ingest?overwrite=true"
```

```json
{
  "status": "success",
  "chunks_indexed": 47,
  "message": "Ingested 47 chunk(s) from 4 document(s) into collection 'transfer_knowledge'."
}
```

---

### `POST /investigate`

Accepts a free-text transfer complaint (minimum 20 characters) and returns a structured investigation result.

```bash
curl -X POST http://localhost:8000/investigate \
  -H "Content-Type: application/json" \
  -d '{"complaint": "Client transferred their RRSP from TD Bank 3 weeks ago. Status shows Transferring but nothing has arrived. Client says TD confirmed funds left their account 2 weeks ago."}'
```

```json
{
  "timeline_reconstruction": "Week 1: Transfer initiated at Wealthsimple...",
  "failure_point": "institution",
  "draft_client_response": "Thank you for reaching out...\n\nAGENT MUST VERIFY: confirm transfer reference number with TD.",
  "confidence_score": 0.78,
  "sources": [
    "institutional_transfer_process.txt",
    "transfer_timelines.txt"
  ],
  "escalation_flags": []
}
```

**Field reference:**

| Field | Type | Description |
|---|---|---|
| `timeline_reconstruction` | string | Step-by-step reconstruction of what likely happened |
| `failure_point` | `wealthsimple` \| `institution` \| `client` \| `unknown` | Where the transfer likely broke down |
| `draft_client_response` | string | Plain-language draft for human review. Ends with `AGENT MUST VERIFY:` checklist |
| `confidence_score` | float 0–1 | Derived from Cohere rerank scores — deterministic for the same complaint |
| `sources` | string[] | Knowledge base documents cited in the analysis |
| `escalation_flags` | string[] | e.g. `large_transaction_review`, `regulatory_reporting_required` |

> **The `draft_client_response` must not be sent to clients without operator review and approval.**
