"""
Basic test stubs for the investigation pipeline.

These tests define the expected contract for each stage of the pipeline.
Implement the logic in app/query.py and app/ingest.py, then fill in the
assertions below.

Run with:
    pytest tests/
"""

import pytest
from app.models import InvestigateRequest, InvestigateResponse, IngestResponse


# ---------------------------------------------------------------------------
# Ingest tests
# ---------------------------------------------------------------------------

class TestIngest:
    """Tests for the document ingestion pipeline (app/ingest.py)."""

    def test_ingest_returns_response_model(self):
        """
        POST /ingest should return a valid IngestResponse.

        TODO: use TestClient to call the endpoint and assert response shape.
        """
        # TODO:
        #   from fastapi.testclient import TestClient
        #   from app.main import app
        #   client = TestClient(app)
        #   response = client.post("/ingest")
        #   assert response.status_code == 200
        #   body = response.json()
        #   assert "documents_ingested" in body
        #   assert isinstance(body["documents_ingested"], int)
        pytest.skip("Not yet implemented")

    def test_ingest_with_no_docs_returns_zero(self):
        """
        When knowledge_base/docs/ is empty, ingestion should succeed with 0 documents.

        TODO: mock DOCS_DIR or point it at a temp empty directory.
        """
        pytest.skip("Not yet implemented")

    def test_ingest_counts_chunks_not_files(self):
        """
        The documents_ingested count should reflect chunks, not raw file count.

        TODO: seed a temp docs directory with a known file, run ingestion,
              assert chunks > 1 for a multi-paragraph file.
        """
        pytest.skip("Not yet implemented")


# ---------------------------------------------------------------------------
# Query / investigation tests
# ---------------------------------------------------------------------------

class TestInvestigate:
    """Tests for the investigation query pipeline (app/query.py)."""

    def test_investigate_returns_response_model(self):
        """
        POST /investigate should return a valid InvestigateResponse.

        TODO: use TestClient with a mocked Cohere client and ChromaDB collection.
        """
        # TODO:
        #   payload = {"complaint": "Transfer of $500 on 2024-10-01 has not arrived after 7 days."}
        #   response = client.post("/investigate", json=payload)
        #   assert response.status_code == 200
        #   data = InvestigateResponse(**response.json())  # validates shape
        pytest.skip("Not yet implemented")

    def test_investigate_requires_complaint_field(self):
        """
        POST /investigate with a missing or empty complaint should return 422.

        TODO: send an empty payload and assert HTTP 422 Unprocessable Entity.
        """
        pytest.skip("Not yet implemented")

    def test_investigate_response_has_citations(self):
        """
        The response should include at least one citation when relevant docs exist.

        TODO: seed ChromaDB with a known document, run investigation, assert citations list is non-empty.
        """
        pytest.skip("Not yet implemented")

    def test_investigate_timeline_is_non_empty(self):
        """
        The reconstructed timeline in the response must not be blank.

        TODO: assert len(response["timeline"].strip()) > 0
        """
        pytest.skip("Not yet implemented")

    def test_investigate_failure_point_is_non_empty(self):
        """
        The identified failure point in the response must not be blank.

        TODO: assert len(response["failure_point"].strip()) > 0
        """
        pytest.skip("Not yet implemented")


# ---------------------------------------------------------------------------
# Model validation tests
# ---------------------------------------------------------------------------

class TestModels:
    """Unit tests for Pydantic models (no I/O required)."""

    def test_investigate_request_rejects_short_complaint(self):
        """
        InvestigateRequest should reject complaints shorter than 10 characters.
        """
        # TODO: assert that pydantic raises ValidationError for short input
        pytest.skip("Not yet implemented")

    def test_investigate_response_citations_default_to_empty_list(self):
        """
        InvestigateResponse.citations should default to [] if not provided.
        """
        response = InvestigateResponse(
            timeline="placeholder",
            failure_point="placeholder",
            draft_response="placeholder",
        )
        assert response.citations == []
