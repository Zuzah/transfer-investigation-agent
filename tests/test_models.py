"""
Tests for Pydantic models in app/models.py.

These tests require no mocking — they verify that the model layer
enforces its own contracts (field validation, type coercion, defaults)
before any pipeline code runs.
"""

import pytest
from pydantic import ValidationError

from app.models import IngestResponse, InvestigateRequest, InvestigationResult


# ---------------------------------------------------------------------------
# InvestigateRequest
# ---------------------------------------------------------------------------

class TestInvestigateRequest:
    """Validates the request payload model for POST /investigate."""

    def test_valid_complaint_is_accepted(self):
        """A complaint meeting the minimum length is accepted without error."""
        req = InvestigateRequest(complaint="Transfer of $500 has not arrived after 7 days.")
        assert req.complaint.startswith("Transfer")

    def test_complaint_at_exact_minimum_length_is_accepted(self):
        """A complaint of exactly 20 characters (the minimum) is valid."""
        req = InvestigateRequest(complaint="12345678901234567890")
        assert len(req.complaint) == 20

    def test_complaint_below_minimum_length_raises(self):
        """A complaint shorter than 20 characters must raise a ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            InvestigateRequest(complaint="too short")
        errors = exc_info.value.errors()
        assert any("min_length" in str(e) or "string_too_short" in e["type"] for e in errors)

    def test_empty_complaint_raises(self):
        """An empty string complaint must raise a ValidationError."""
        with pytest.raises(ValidationError):
            InvestigateRequest(complaint="")

    def test_missing_complaint_field_raises(self):
        """Omitting the complaint field entirely must raise a ValidationError."""
        with pytest.raises(ValidationError):
            InvestigateRequest()


# ---------------------------------------------------------------------------
# InvestigationResult
# ---------------------------------------------------------------------------

class TestInvestigationResult:
    """Validates the investigation result model returned by POST /investigate."""

    def _valid_result(self, **overrides) -> dict:
        """Return a dict of valid field values, with optional overrides."""
        base = dict(
            timeline_reconstruction="Day 1: Transfer initiated. Day 5: Not yet received.",
            failure_point="institution",
            draft_client_response="Your transfer is delayed.\n\nAGENT MUST VERIFY: dates.",
            confidence_score=0.8,
        )
        return {**base, **overrides}

    @pytest.mark.parametrize("failure_point", ["wealthsimple", "institution", "client", "unknown"])
    def test_all_valid_failure_points_accepted(self, failure_point: str):
        """Each allowed failure_point literal value must be accepted by the model."""
        result = InvestigationResult(**self._valid_result(failure_point=failure_point))
        assert result.failure_point == failure_point

    def test_invalid_failure_point_raises(self):
        """A failure_point outside the allowed literals must raise a ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            InvestigationResult(**self._valid_result(failure_point="bank_error"))
        errors = exc_info.value.errors()
        assert any("failure_point" in str(e) or "literal_error" in e["type"] for e in errors)

    def test_confidence_score_at_zero_is_valid(self):
        """confidence_score of 0.0 (the lower bound) must be accepted."""
        result = InvestigationResult(**self._valid_result(confidence_score=0.0))
        assert result.confidence_score == 0.0

    def test_confidence_score_at_one_is_valid(self):
        """confidence_score of 1.0 (the upper bound) must be accepted."""
        result = InvestigationResult(**self._valid_result(confidence_score=1.0))
        assert result.confidence_score == 1.0

    def test_confidence_score_above_1_raises(self):
        """confidence_score above 1.0 must be rejected — the model enforces le=1.0."""
        with pytest.raises(ValidationError):
            InvestigationResult(**self._valid_result(confidence_score=1.01))

    def test_confidence_score_below_0_raises(self):
        """confidence_score below 0.0 must be rejected — the model enforces ge=0.0."""
        with pytest.raises(ValidationError):
            InvestigationResult(**self._valid_result(confidence_score=-0.01))

    def test_sources_defaults_to_empty_list(self):
        """If sources is not provided, the model must default to an empty list."""
        result = InvestigationResult(**self._valid_result())
        assert result.sources == []

    def test_escalation_flags_defaults_to_empty_list(self):
        """If escalation_flags is not provided, the model must default to an empty list."""
        result = InvestigationResult(**self._valid_result())
        assert result.escalation_flags == []

    def test_sources_and_flags_populated_when_provided(self):
        """Explicitly provided sources and escalation_flags are stored correctly."""
        result = InvestigationResult(
            **self._valid_result(
                sources=["transfer_timelines.txt"],
                escalation_flags=["potential_fraud"],
            )
        )
        assert result.sources == ["transfer_timelines.txt"]
        assert result.escalation_flags == ["potential_fraud"]

    def test_missing_required_fields_raises(self):
        """Omitting any required field must raise a ValidationError."""
        with pytest.raises(ValidationError):
            InvestigationResult(
                timeline_reconstruction="Timeline here.",
                # failure_point, draft_client_response, confidence_score omitted
            )


# ---------------------------------------------------------------------------
# IngestResponse
# ---------------------------------------------------------------------------

class TestIngestResponse:
    """Validates the response model returned by POST /ingest."""

    def test_valid_ingest_response_constructed(self):
        """A fully populated IngestResponse must be constructed without error."""
        resp = IngestResponse(success=True, documents_ingested=42, message="Done.")
        assert resp.success is True
        assert resp.documents_ingested == 42

    def test_zero_documents_ingested_is_valid(self):
        """documents_ingested=0 is a valid state (nothing new to ingest)."""
        resp = IngestResponse(success=True, documents_ingested=0, message="Nothing new.")
        assert resp.documents_ingested == 0

    def test_success_false_is_valid(self):
        """success=False is a valid state representing a failed ingestion."""
        resp = IngestResponse(success=False, documents_ingested=0, message="Error occurred.")
        assert resp.success is False
