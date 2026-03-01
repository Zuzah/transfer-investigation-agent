"""
Pydantic request and response models for the Transfer Investigation Agent.
"""

from typing import List, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# /ingest
# ---------------------------------------------------------------------------

class IngestResponse(BaseModel):
    """Internal pipeline response returned by ingest_documents()."""

    success: bool = Field(..., description="Whether ingestion completed without errors.")
    documents_ingested: int = Field(..., description="Number of document chunks upserted into ChromaDB.")
    message: str = Field(..., description="Human-readable status message.")


class IngestRouteResponse(BaseModel):
    """HTTP response returned by POST /ingest."""

    status: str = Field(..., description="'success' or 'error'.")
    chunks_indexed: int = Field(..., description="Number of new chunks added to the collection.")
    message: str = Field(..., description="Human-readable status message.")


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Response returned by GET /health."""

    status: str = Field(default="ok", description="Always 'ok' if the service is running.")
    knowledge_base_size: int = Field(
        ...,
        description="Number of chunks currently stored in the ChromaDB collection. 0 if not yet ingested.",
    )


# ---------------------------------------------------------------------------
# /investigate — request
# ---------------------------------------------------------------------------

class InvestigateRequest(BaseModel):
    """Payload for a transfer complaint investigation."""

    complaint: str = Field(
        ...,
        min_length=20,
        description=(
            "Free-text description of the transfer complaint. "
            "Should include any available reference numbers, dates, amounts, and parties involved."
        ),
        examples=["Customer reports transfer of $4,200 to account ending 8821 initiated on 2024-11-03 has not arrived after 5 business days."],
    )


# ---------------------------------------------------------------------------
# /investigate — response
# ---------------------------------------------------------------------------

class Citation(BaseModel):
    """A single source document cited in the investigation output."""

    document_name: str = Field(..., description="Filename of the source document.")
    excerpt: str = Field(..., description="Relevant excerpt from the source document.")


class InvestigationResult(BaseModel):
    """
    Structured output of the transfer investigation pipeline.

    Produced by the query pipeline (app/query.py) and returned by POST /investigate.
    All fields are for internal ops use. The draft_client_response must not be sent
    to clients without human review and approval.
    """

    timeline_reconstruction: str = Field(
        ...,
        description=(
            "Step-by-step reconstruction of what likely happened, "
            "comparing expected process timing against the complaint details."
        ),
    )
    failure_point: Literal["wealthsimple", "institution", "client", "unknown"] = Field(
        ...,
        description=(
            "The party most likely responsible for the delay or failure. "
            "One of: 'wealthsimple', 'institution', 'client', 'unknown'."
        ),
    )
    draft_client_response: str = Field(
        ...,
        description=(
            "Plain-language draft response for the client. "
            "For human review and approval only — must not be sent automatically."
        ),
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Model confidence in the analysis (0.0–1.0). "
            "Reflects completeness of the complaint, strength of documentary evidence, "
            "and whether the failure point is unambiguous."
        ),
    )
    sources: List[str] = Field(
        default_factory=list,
        description="Filenames of the knowledge base documents used to inform this analysis.",
    )
    escalation_flags: List[str] = Field(
        default_factory=list,
        description=(
            "Fraud indicators, regulatory edge cases, or supervisor-escalation triggers. "
            "Empty list if none identified."
        ),
    )
