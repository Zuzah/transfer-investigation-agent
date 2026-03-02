"""
Pydantic request and response models for the Transfer Investigation Agent.
"""

from datetime import datetime
from typing import List, Literal, Optional

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
    case_id: Optional[str] = Field(
        default=None,
        description=(
            "If provided, the investigation result will be saved to this case record "
            "and the case status will be updated to 'investigated'."
        ),
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
    recommended_action: Literal["send_response", "escalate", "investigate_further"] = Field(
        default="investigate_further",
        description=(
            "AI-recommended next action for the analyst. "
            "send_response: evidence sufficient, send the draft. "
            "escalate: route to a specialist team. "
            "investigate_further: gather more information first."
        ),
    )
    relevant_departments: List[str] = Field(
        default_factory=list,
        description=(
            "Departments suggested for escalation or coordination. "
            "Empty when recommended_action is send_response."
        ),
    )


# ---------------------------------------------------------------------------
# /cases — request / response models
# ---------------------------------------------------------------------------

class CaseCreate(BaseModel):
    """Payload for POST /cases — submitted by the client."""

    client_id: str = Field(..., description="Client identifier (e.g. 'Client #4821').")
    category: str = Field(..., description="Triage category for the complaint.")
    complaint: str = Field(..., min_length=10, description="Free-text complaint description.")


class CaseResponse(BaseModel):
    """Case record returned by GET /cases and related endpoints."""

    id: str = Field(..., description="UUID of the case.")
    client_id: str
    category: str
    complaint: str
    status: str = Field(..., description="One of: open | investigated | resolved | escalated.")
    result_json: Optional[dict] = Field(default=None, description="Serialised InvestigationResult, null until investigated.")
    action_taken: Optional[str] = Field(default=None, description="'replied' or 'escalated', null until actioned.")
    department: Optional[str] = Field(default=None, description="Department routed to on escalation.")
    created_at: datetime
    resolved_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# /cases/{id}/escalate — request model
# ---------------------------------------------------------------------------

class EscalateRequest(BaseModel):
    """Payload for PATCH /cases/{id}/escalate."""

    department: str = Field(..., description="The department this case is being escalated to.")


# ---------------------------------------------------------------------------
# /admin/reset — response model
# ---------------------------------------------------------------------------

class AdminResetResponse(BaseModel):
    """Response from POST /admin/reset."""

    seeded: int = Field(..., description="Number of demo cases inserted.")
    message: str
