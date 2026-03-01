"""
Transfer Investigation Agent — FastAPI entry point.

Routes:
  POST /ingest        — loads documents from knowledge_base/docs/ into ChromaDB
  POST /investigate   — accepts a transfer complaint and returns a cited draft response

The investigation pipeline uses Cohere's RAG capabilities to:
  1. Retrieve relevant process documentation from the vector store
  2. Reconstruct the transfer timeline from the complaint and retrieved docs
  3. Identify the likely failure point (wealthsimple / institution / client / unknown)
  4. Produce a draft response for human review and approval — never sent automatically
"""

from fastapi import FastAPI

from app.ingest import ingest_documents
from app.models import IngestResponse, InvestigateRequest, InvestigationResult
from app.query import run_investigation

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
    generates embeddings via Cohere Embed v3, and upserts them into ChromaDB.

    Returns a summary of how many document chunks were ingested.
    Already-present chunks are skipped (idempotent). Use the --overwrite flag
    via the CLI to rebuild from scratch.
    """
    return await ingest_documents()


@app.post("/investigate", response_model=InvestigationResult)
async def investigate(request: InvestigateRequest):
    """
    Investigate a transfer complaint.

    Accepts a free-text complaint describing a transfer issue. The pipeline:
      1. Embeds the complaint using Cohere Embed v3
      2. Retrieves the top 20 candidate chunks from ChromaDB
      3. Reranks to the top 5 using Cohere Rerank v3
      4. Passes the complaint + context to Command R+ with a grounded prompt
      5. Returns a structured result with timeline, failure point, draft reply,
         confidence score, cited sources, and any escalation flags

    The draft_client_response field is for human review only.
    It must not be sent to clients without operator approval.
    """
    return await run_investigation(request)
