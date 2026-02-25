"""
Transfer Investigation Agent — FastAPI entry point.

This app exposes two routes:
  POST /ingest        — loads documents from knowledge_base/docs/ into ChromaDB
  POST /investigate   — accepts a transfer complaint and returns a cited draft response

The investigation pipeline uses Cohere's RAG capabilities to:
  1. Retrieve relevant process documentation from the vector store
  2. Reconstruct the transfer timeline from the complaint and retrieved docs
  3. Identify the likely failure point
  4. Produce a cited draft response for human review and approval
"""

from fastapi import FastAPI
from app.ingest import ingest_documents
from app.query import run_investigation
from app.models import IngestResponse, InvestigateRequest, InvestigateResponse

app = FastAPI(
    title="Transfer Investigation Agent",
    description=(
        "Internal ops tool that investigates stuck/failed transfers, "
        "reconstructs the transfer timeline, identifies the likely failure point, "
        "and returns a cited draft response for human review and approval."
    ),
    version="0.1.0",
)


@app.post("/ingest", response_model=IngestResponse)
async def ingest():
    """
    Trigger document ingestion.

    Reads all .txt files from knowledge_base/docs/, chunks them,
    generates embeddings via Cohere, and upserts them into ChromaDB.

    Returns a summary of how many documents were ingested.

    TODO: implement ingestion logic in app/ingest.py
    """
    # TODO: call ingest_documents() and return result
    return await ingest_documents()


@app.post("/investigate", response_model=InvestigateResponse)
async def investigate(request: InvestigateRequest):
    """
    Investigate a transfer complaint.

    Accepts a free-text complaint describing a transfer issue. The pipeline:
      1. Embeds the complaint using Cohere
      2. Retrieves the most relevant process documents from ChromaDB
      3. Passes complaint + retrieved context to Cohere's chat/RAG endpoint
      4. Returns a structured response with: timeline, failure point, draft reply, and citations

    The returned draft is for human review — it must not be sent to clients automatically.

    TODO: implement investigation logic in app/query.py
    """
    # TODO: call run_investigation(request) and return result
    return await run_investigation(request)
