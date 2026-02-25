"""
Pydantic request and response models for the Transfer Investigation Agent.
"""

from pydantic import BaseModel, Field
from typing import List


# ---------------------------------------------------------------------------
# /ingest
# ---------------------------------------------------------------------------

class IngestResponse(BaseModel):
    """Response returned after document ingestion."""

    success: bool = Field(..., description="Whether ingestion completed without errors.")
    documents_ingested: int = Field(..., description="Number of document chunks upserted into ChromaDB.")
    message: str = Field(..., description="Human-readable status message.")


# ---------------------------------------------------------------------------
# /investigate
# ---------------------------------------------------------------------------

class InvestigateRequest(BaseModel):
    """Payload for a transfer complaint investigation."""

    complaint: str = Field(
        ...,
        min_length=10,
        description=(
            "Free-text description of the transfer complaint. "
            "Should include any available reference numbers, dates, amounts, and parties involved."
        ),
        examples=["Customer reports transfer of $4,200 to account ending 8821 initiated on 2024-11-03 has not arrived after 5 business days."],
    )


class Citation(BaseModel):
    """A single source document cited in the investigation output."""

    document_name: str = Field(..., description="Filename of the source document.")
    excerpt: str = Field(..., description="Relevant excerpt from the source document.")


class InvestigateResponse(BaseModel):
    """Structured output of the transfer investigation pipeline."""

    timeline: str = Field(
        ...,
        description="Reconstructed transfer timeline based on the complaint and retrieved documentation.",
    )
    failure_point: str = Field(
        ...,
        description="The likely step in the transfer process where the failure occurred.",
    )
    draft_response: str = Field(
        ...,
        description=(
            "A draft client-facing response for human review and approval. "
            "Must not be sent to clients without human sign-off."
        ),
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Source documents retrieved from the knowledge base that informed this response.",
    )
