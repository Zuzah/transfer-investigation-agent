"""
Transfer Investigation Agent — FastAPI entry point.

Routes:
  GET  /          — serves the operator UI (app/static/index.html)
  GET  /health    — returns service status and knowledge base chunk count
  POST /ingest    — loads knowledge_base/docs/ into ChromaDB (?overwrite=false)
  POST /investigate — accepts a complaint and returns a cited draft response

CORS is open (internal demo tool — not exposed to the public internet).
Static files are served from app/static/.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.ingest import ingest_documents
from app.models import (
    HealthResponse,
    IngestRouteResponse,
    InvestigateRequest,
    InvestigationResult,
)
from app.query import knowledge_base_size, run_investigation

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


# ---------------------------------------------------------------------------
# Startup — auto-ingest if the knowledge base is empty
# ---------------------------------------------------------------------------

async def _auto_ingest_if_empty() -> None:
    """
    Ingest knowledge base documents on startup if ChromaDB is empty.

    This ensures the app is immediately usable after a cold start (e.g. on
    Render's free tier where the filesystem resets on each deploy). If the
    collection already contains chunks, ingestion is skipped. Errors are
    logged but do not prevent the server from starting.
    """
    size = knowledge_base_size()
    if size > 0:
        logger.info("Knowledge base ready: %d chunks already indexed.", size)
        return

    logger.info(
        "Knowledge base is empty — running auto-ingest. "
        "This may take 30–60 seconds on first deploy."
    )
    try:
        result = await ingest_documents(overwrite=False)
        logger.info("Auto-ingest complete: %s", result.message)
    except Exception as exc:
        logger.error(
            "Auto-ingest failed: %s — "
            "call POST /ingest manually before using /investigate.",
            exc,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: run startup tasks, then yield to serve requests."""
    await _auto_ingest_if_empty()
    yield


# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

app = FastAPI(
    lifespan=lifespan,
    title="Transfer Investigation Agent",
    description=(
        "Internal ops tool that investigates stuck/failed transfers, "
        "reconstructs the transfer timeline, identifies the likely failure point, "
        "and returns a cited draft response for human review and approval."
    ),
    version="0.1.0",
)

# CORS — open for all origins (internal demo only; restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files — served at /static, index.html at /
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def serve_ui():
    """Serve the operator UI from app/static/index.html."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health", response_model=HealthResponse)
async def health():
    """
    Return service health and knowledge base readiness.

    knowledge_base_size is the number of chunks in the ChromaDB collection.
    A value of 0 means ingestion has not been run yet.
    """
    return HealthResponse(
        status="ok",
        knowledge_base_size=knowledge_base_size(),
    )


@app.post("/ingest", response_model=IngestRouteResponse)
async def ingest(
    overwrite: bool = Query(
        default=False,
        description=(
            "If true, deletes the existing ChromaDB collection and rebuilds it "
            "from scratch. If false (default), skips chunks already present."
        ),
    ),
):
    """
    Trigger document ingestion from knowledge_base/docs/.

    Reads all .txt files, chunks them (~300 tokens, 50-token overlap),
    embeds via Cohere Embed v3, and upserts into ChromaDB.

    Use ?overwrite=true to delete and rebuild the collection from scratch.
    """
    result = await ingest_documents(overwrite=overwrite)
    return IngestRouteResponse(
        status="success",
        chunks_indexed=result.documents_ingested,
        message=result.message,
    )


@app.post("/investigate", response_model=InvestigationResult)
async def investigate(request: InvestigateRequest):
    """
    Investigate a transfer complaint.

    Accepts a free-text complaint (minimum 20 characters). The pipeline:
      1. Embeds the complaint using Cohere Embed v3
      2. Retrieves the top 20 candidate chunks from ChromaDB
      3. Reranks to the top 5 using Cohere Rerank v3
      4. Passes the complaint + context to Command R+ (command-r-plus-08-2024)
      5. Returns a structured result with timeline, failure point, draft reply,
         confidence score, cited sources, and any escalation flags

    The draft_client_response field is for human review only.
    It must not be sent to clients without operator approval.
    """
    # Log complaint preview (truncated) and confidence on completion — never the full text.
    logger.info("Received complaint: %.100s...", request.complaint)

    result = await run_investigation(request)

    logger.info(
        "Investigation complete — failure_point=%s confidence=%.2f",
        result.failure_point,
        result.confidence_score,
    )
    print(
        f"[investigate] complaint={request.complaint[:100]!r}... "
        f"failure_point={result.failure_point} "
        f"confidence={result.confidence_score:.2f}"
    )

    return result
