# Transfer Investigation Agent

Internal ops tool that takes a Wealthsimple transfer complaint, retrieves relevant 
process documentation via Cohere RAG, reconstructs the transfer timeline, identifies 
the likely failure point, and returns a cited draft response for human review.

## Stack
- Python + FastAPI
- Cohere (Embed v3, Rerank, Command R+)
- ChromaDB (local vector store, persists to ./chroma_db/)
- pytest for testing
- Next.js 14 + TypeScript (frontend, lives in frontend/)

## Dev Workflow

### Running the app (production build)
```bash
fastapi dev app/main.py
```

### Running the app (active frontend development — two terminals)
```bash
# Terminal 1 — backend
fastapi dev app/main.py          # http://localhost:8000

# Terminal 2 — frontend
cd frontend && npm run dev       # http://localhost:3000 (open this in browser)
```
Next.js rewrites in `next.config.mjs` proxy all API paths (`/investigate`, `/ingest`,
`/health`, `/cases`, `/admin/reset`) to FastAPI at localhost:8000 automatically.

### Building the frontend
```bash
cd frontend && npm run build     # compiles TypeScript → app/static/
```
Run this before starting FastAPI if you want to serve the latest frontend from http://localhost:8000.

### Running tests
```bash
pytest tests/ -v
```

### Ingesting the knowledge base
```bash
python -m app.ingest              # incremental
python -m app.ingest --overwrite  # rebuild from scratch
```

## Frontend

- Next.js 14 + TypeScript lives in `frontend/`
- Dev: `npm run dev` from `frontend/` (port 3000, rewrites proxy API calls to port 8000)
- Build: `npm run build` from `frontend/` (outputs static export to `app/static/`)
- Never put API calls in components — all fetch calls go in `frontend/lib/api.ts`
- TypeScript interfaces mirroring `app/models.py` live in `frontend/lib/types.ts` — keep them in sync when models change

## Test-Driven Development

Always follow TDD:
1. Write a failing test first
2. Implement only enough to make it pass
3. Refactor, confirm tests still pass

**Mock all external calls.** Tests must run without a Cohere API key or live ChromaDB.
Use `unittest.mock` or `pytest-mock` to mock:
- `cohere.Client` and all its methods
- `chromadb.PersistentClient` and collection methods

Each test must have a docstring explaining what it verifies.

Cover at minimum:
- Happy path
- Empty or missing input
- API failure (simulate Cohere throwing an exception)
- Edge cases specific to the function

## Code Style
- Type hints on all functions
- Docstrings on all public functions
- Pydantic models for all request/response shapes (defined in models.py)
- Environment variables loaded via python-dotenv, never hardcoded
- Raise descriptive exceptions — no silent failures

## Boundaries (Do Not Cross)
- The AI drafts responses. It never sends them.
- Financial remedy logic must never be automated — always a human decision.
- Do not log full complaint text to console — truncate to 100 chars max.

## After Every Mistake
End your correction with: "Update CLAUDE.md so you don't make this mistake again."