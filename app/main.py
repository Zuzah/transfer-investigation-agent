"""
Transfer Investigation Agent — FastAPI entry point.

Routes:
  GET  /                     — serves the operator UI (app/static/index.html)
  GET  /client               — serves the client page (app/static/client.html)
  GET  /analyst              — serves the analyst page (app/static/analyst.html)
  GET  /admin                — serves the admin page (app/static/admin.html)
  GET  /health               — service status + knowledge base chunk count
  POST /ingest               — loads knowledge_base/docs/ into ChromaDB
  POST /investigate          — runs the RAG+LLM investigation pipeline
  POST /cases                — client submits a new complaint case
  GET  /cases                — analyst fetches the case queue (filterable by status)
  GET  /cases/{id}           — get a single case record
  PATCH /cases/{id}/resolve  — mark a case resolved (action_taken=replied)
  PATCH /cases/{id}/escalate — mark a case escalated (route to a department)
  POST /admin/reset          — wipe all cases and re-seed 5 demo cases

CORS is open (internal demo tool — not exposed to the public internet).
Static files are served from app/static/ when the Next.js build output exists.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Case, create_tables, get_session
from app.ingest import ingest_documents
from app.models import (
    AdminResetResponse,
    CaseCreate,
    CaseResponse,
    EscalateRequest,
    HealthResponse,
    IngestRouteResponse,
    InvestigateRequest,
    InvestigationResult,
)
from app.query import knowledge_base_size, run_investigation
from app.seeds import SEED_CASES

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


# ---------------------------------------------------------------------------
# Startup tasks
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
    """FastAPI lifespan: create DB tables, run auto-ingest, then yield."""
    await create_tables()
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
    version="0.2.0",
)

# CORS — open for all origins (internal demo only; restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Next.js compiled assets — JS bundles, CSS, and chunk files.
# Next.js hard-codes "/_next/" as the base path for all compiled assets in the
# HTML it generates, so this mount must be at "/_next", not "/static".
_next_dir = STATIC_DIR / "_next"
if _next_dir.exists():
    app.mount("/_next", StaticFiles(directory=str(_next_dir)), name="next_assets")


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _case_to_response(case: Case) -> CaseResponse:
    """Convert a Case ORM object to a CaseResponse Pydantic model."""
    return CaseResponse(
        id=case.id,
        client_id=case.client_id,
        category=case.category,
        complaint=case.complaint,
        status=case.status,
        result_json=case.result_json,
        action_taken=case.action_taken,
        department=case.department,
        created_at=case.created_at,
        resolved_at=case.resolved_at,
    )


# ---------------------------------------------------------------------------
# Routes — static + health
# ---------------------------------------------------------------------------

def _serve_page(name: str | None = None) -> FileResponse:
    """
    Serve a Next.js static-export page by name.

    Next.js 14 App Router with output='export' (and no trailingSlash) writes:
      /          → app/static/index.html
      /client    → app/static/client.html
      /analyst   → app/static/analyst.html
      /admin     → app/static/admin.html

    Falls back to the subdirectory pattern (client/index.html) in case a
    future Next.js version or trailingSlash:true config changes the layout.

    Raises 503 when the frontend has not been built yet (app/static/ absent).
    """
    from fastapi.responses import JSONResponse

    if name:
        # Flat file — default App Router export layout
        flat = STATIC_DIR / f"{name}.html"
        # Subdirectory fallback (trailingSlash:true or Pages Router layout)
        subdir = STATIC_DIR / name / "index.html"
        path = flat if flat.exists() else subdir
    else:
        path = STATIC_DIR / "index.html"

    if path.exists():
        return FileResponse(str(path))

    return JSONResponse(
        {"detail": "Frontend not built. Run `cd frontend && npm run build`."},
        status_code=503,
    )


@app.get("/", include_in_schema=False)
async def serve_ui():
    """Serve the role-chooser landing page (app/static/index.html)."""
    return _serve_page()


@app.get("/client", include_in_schema=False)
async def serve_client():
    """Serve the client complaint submission page (app/static/client/index.html)."""
    return _serve_page("client")


@app.get("/analyst", include_in_schema=False)
async def serve_analyst():
    """Serve the analyst investigation workspace (app/static/analyst/index.html)."""
    return _serve_page("analyst")


@app.get("/admin", include_in_schema=False)
async def serve_admin():
    """Serve the admin database panel (app/static/admin/index.html)."""
    return _serve_page("admin")


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


# ---------------------------------------------------------------------------
# Routes — knowledge base ingestion
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Routes — investigation
# ---------------------------------------------------------------------------

@app.post("/investigate", response_model=InvestigationResult)
async def investigate(
    request: InvestigateRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Investigate a transfer complaint.

    Accepts a free-text complaint (minimum 20 characters). The pipeline:
      1. Embeds the complaint using Cohere Embed v3
      2. Retrieves the top 20 candidate chunks from ChromaDB
      3. Reranks to the top 5 using Cohere Rerank v3
      4. Passes the complaint + context to Command R+
      5. Returns a structured result with timeline, failure point, draft reply,
         confidence score, cited sources, and escalation flags

    If case_id is provided, the result is saved to that case record and the
    case status is updated to 'investigated'.

    The draft_client_response field is for human review only.
    It must not be sent to clients without operator approval.
    """
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

    # Persist result to the case record when case_id is supplied
    if request.case_id:
        case = await session.get(Case, request.case_id)
        if case:
            case.result_json = result.model_dump(mode="json")
            case.status = "investigated"
        else:
            logger.warning("case_id %r not found — result not persisted.", request.case_id)

    return result


# ---------------------------------------------------------------------------
# Routes — cases (CRUD)
# ---------------------------------------------------------------------------

@app.post("/cases", response_model=CaseResponse, status_code=201)
async def create_case(
    payload: CaseCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new complaint case.

    Called by the client view when a user submits a transfer complaint.
    Returns the new case record with status='open'.
    """
    case = Case(
        client_id=payload.client_id,
        category=payload.category,
        complaint=payload.complaint,
    )
    session.add(case)
    await session.flush()  # assigns the generated id before commit
    return _case_to_response(case)


@app.get("/cases", response_model=list[CaseResponse])
async def list_cases(
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: open | investigated | resolved | escalated",
    ),
    session: AsyncSession = Depends(get_session),
):
    """
    List all complaint cases, ordered newest first.

    Pass ?status=open (or investigated, resolved, escalated) to filter.
    Returns all cases when the status parameter is omitted.
    """
    stmt = select(Case).order_by(Case.created_at.desc())
    if status:
        stmt = stmt.where(Case.status == status)
    rows = await session.execute(stmt)
    return [_case_to_response(c) for c in rows.scalars()]


@app.get("/cases/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Return a single case by ID. Raises 404 if not found."""
    case = await session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found.")
    return _case_to_response(case)


@app.patch("/cases/{case_id}/resolve", response_model=CaseResponse)
async def resolve_case(
    case_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Mark a case as resolved (analyst sent the draft response to the client).

    Sets status='resolved', action_taken='replied', resolved_at=now.
    """
    case = await session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found.")
    case.status = "resolved"
    case.action_taken = "replied"
    case.resolved_at = datetime.now(timezone.utc)
    return _case_to_response(case)


@app.patch("/cases/{case_id}/escalate", response_model=CaseResponse)
async def escalate_case(
    case_id: str,
    payload: EscalateRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Mark a case as escalated and record which department it was routed to.

    Sets status='escalated', action_taken='escalated', department=payload.department.
    """
    case = await session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found.")
    case.status = "escalated"
    case.action_taken = "escalated"
    case.department = payload.department
    case.resolved_at = datetime.now(timezone.utc)
    return _case_to_response(case)


# ---------------------------------------------------------------------------
# Routes — admin
# ---------------------------------------------------------------------------

@app.post("/admin/reset", response_model=AdminResetResponse)
async def admin_reset(session: AsyncSession = Depends(get_session)):
    """
    Reset the demo database.

    Deletes all existing cases and re-seeds with demo cases from app/seeds.py.
    This is a destructive operation — all investigation results and actions
    are permanently removed.
    """
    # Delete all existing cases
    rows = await session.execute(select(Case))
    for case in rows.scalars():
        await session.delete(case)
    await session.flush()

    # Insert seed cases
    for seed in SEED_CASES:
        session.add(Case(**seed))
    await session.flush()

    logger.info("Admin reset complete — %d demo cases seeded.", len(SEED_CASES))
    return AdminResetResponse(
        seeded=len(SEED_CASES),
        message=f"Database reset. {len(SEED_CASES)} demo cases seeded.",
    )
