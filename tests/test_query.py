"""
Tests for the investigation query pipeline in app/query.py,
and for the POST /investigate HTTP endpoint in app/main.py.

All Cohere and ChromaDB calls are mocked — these tests run without
a live API key or a running database instance.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import InvestigateRequest, InvestigationResult
from app.query import (
    _build_chroma_collection,
    _build_cohere_client,
    _build_messages,
    _embed_query,
    _parse_model_output,
    _rerank,
    _retrieve_candidates,
    investigate,
    run_investigation,
)


# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------

SAMPLE_COMPLAINT = (
    "Customer reports transfer of $4,200 to account ending 8821 "
    "initiated on 2024-11-03 has not arrived after 5 business days."
)

SAMPLE_CHUNKS = [
    {
        "text": "Bank deposits (PAD) take 5–7 business days to become available.",
        "source": "transfer_timelines.txt",
        "score": 0.92,
        "rerank_score": 0.95,
    },
    {
        "text": "Institutional transfers can take 1–4 weeks; institution may reject the request.",
        "source": "institutional_transfer_process.txt",
        "score": 0.88,
        "rerank_score": 0.91,
    },
]

VALID_MODEL_JSON = {
    "timeline_reconstruction": "Day 1: Transfer initiated. Day 5: Not yet received.",
    "failure_point": "institution",
    "draft_client_response": (
        "We are looking into your transfer.\n\n"
        "AGENT MUST VERIFY: confirm transfer date and account number."
    ),
    "confidence_score": 0.85,
    "escalation_flags": [],
}


def _make_embed_response(vector: list | None = None) -> MagicMock:
    """Return a mock Cohere embed response with one embedding vector."""
    mock = MagicMock()
    mock.embeddings = [vector or [0.1, 0.2, 0.3]]
    return mock


def _make_rerank_result(index: int, score: float) -> MagicMock:
    """Return a mock Cohere rerank result entry."""
    result = MagicMock()
    result.index = index
    result.relevance_score = score
    return result


def _make_mock_collection(count: int = 5) -> MagicMock:
    """Return a mock ChromaDB collection pre-configured for retrieval."""
    collection = MagicMock()
    collection.count.return_value = count
    collection.query.return_value = {
        "documents": [[c["text"] for c in SAMPLE_CHUNKS]],
        "metadatas": [[{"source": c["source"]} for c in SAMPLE_CHUNKS]],
        "distances": [[1.0 - c["score"] for c in SAMPLE_CHUNKS]],
    }
    return collection


# ---------------------------------------------------------------------------
# _build_cohere_client
# ---------------------------------------------------------------------------

class TestBuildCohereClient:
    """Tests for Cohere client construction in query.py."""

    def test_raises_if_api_key_missing(self, monkeypatch):
        """EnvironmentError is raised when COHERE_API_KEY is absent."""
        monkeypatch.delenv("COHERE_API_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="COHERE_API_KEY"):
            _build_cohere_client()

    def test_returns_client_when_key_present(self, monkeypatch):
        """A cohere.Client is returned when the API key is set."""
        monkeypatch.setenv("COHERE_API_KEY", "test-key")
        with patch("app.query.cohere.Client") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = _build_cohere_client()
        mock_cls.assert_called_once_with("test-key")
        assert client is mock_cls.return_value


# ---------------------------------------------------------------------------
# _build_chroma_collection
# ---------------------------------------------------------------------------

class TestBuildChromaCollection:
    """Tests for ChromaDB collection retrieval in query.py."""

    def test_returns_collection_when_exists(self):
        """
        get_collection is called with the correct collection name,
        and the result is returned to the caller.
        """
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_collection.return_value = mock_collection

        with patch("app.query.chromadb.PersistentClient", return_value=mock_client):
            result = _build_chroma_collection()

        mock_client.get_collection.assert_called_once_with(name="transfer_knowledge")
        assert result is mock_collection

    def test_raises_runtime_error_when_collection_missing(self):
        """
        If the collection does not exist (get_collection raises), a RuntimeError
        with a helpful 'run ingest first' message is raised instead.
        """
        mock_client = MagicMock()
        mock_client.get_collection.side_effect = Exception("does not exist")

        with patch("app.query.chromadb.PersistentClient", return_value=mock_client):
            with pytest.raises(RuntimeError, match="python -m app.ingest"):
                _build_chroma_collection()


# ---------------------------------------------------------------------------
# _embed_query
# ---------------------------------------------------------------------------

class TestEmbedQuery:
    """Tests for the complaint embedding step."""

    def test_calls_cohere_with_search_query_input_type(self):
        """
        _embed_query must use input_type='search_query' (not 'search_document')
        so the embedding is optimised for retrieval rather than indexing.
        """
        co = MagicMock()
        co.embed.return_value = _make_embed_response([0.5, 0.6])

        result = _embed_query(co, SAMPLE_COMPLAINT)

        co.embed.assert_called_once_with(
            texts=[SAMPLE_COMPLAINT],
            model="embed-english-v3.0",
            input_type="search_query",
        )
        assert result == [0.5, 0.6]

    def test_returns_first_embedding_vector(self):
        """_embed_query returns the first element of the embeddings list."""
        co = MagicMock()
        co.embed.return_value = _make_embed_response([1.0, 2.0, 3.0])

        result = _embed_query(co, "A complaint about a transfer.")

        assert result == [1.0, 2.0, 3.0]

    def test_cohere_error_propagates(self):
        """If Cohere raises, the exception is not swallowed and propagates to the caller."""
        co = MagicMock()
        co.embed.side_effect = Exception("Cohere unavailable")

        with pytest.raises(Exception, match="Cohere unavailable"):
            _embed_query(co, SAMPLE_COMPLAINT)


# ---------------------------------------------------------------------------
# _retrieve_candidates
# ---------------------------------------------------------------------------

class TestRetrieveCandidates:
    """Tests for the ChromaDB retrieval step."""

    def test_returns_list_of_chunk_dicts(self):
        """
        _retrieve_candidates must return a list of dicts with 'text', 'source',
        and 'score' keys derived from the ChromaDB query result.
        """
        collection = _make_mock_collection()
        embedding = [0.1, 0.2, 0.3]

        results = _retrieve_candidates(collection, embedding, n=20)

        assert len(results) == len(SAMPLE_CHUNKS)
        assert all("text" in r and "source" in r and "score" in r for r in results)

    def test_score_is_converted_from_cosine_distance(self):
        """
        ChromaDB returns cosine distances; _retrieve_candidates must convert
        them to similarity scores (score = 1.0 - distance).
        """
        collection = MagicMock()
        collection.count.return_value = 1
        collection.query.return_value = {
            "documents": [["some text"]],
            "metadatas": [[{"source": "doc.txt"}]],
            "distances": [[0.25]],  # distance=0.25 → score=0.75
        }

        results = _retrieve_candidates(collection, [0.1], n=1)

        assert pytest.approx(results[0]["score"]) == 0.75

    def test_n_results_capped_at_collection_count(self):
        """
        If the collection has fewer chunks than n, the query uses
        collection.count() rather than n to avoid an out-of-range error.
        """
        collection = MagicMock()
        collection.count.return_value = 3  # smaller than default n=20
        collection.query.return_value = {
            "documents": [["t1", "t2", "t3"]],
            "metadatas": [[{"source": "a.txt"}, {"source": "b.txt"}, {"source": "c.txt"}]],
            "distances": [[0.1, 0.2, 0.3]],
        }

        _retrieve_candidates(collection, [0.1], n=20)

        call_kwargs = collection.query.call_args.kwargs
        assert call_kwargs["n_results"] == 3  # capped at collection size

    def test_source_defaults_to_unknown_when_metadata_missing(self):
        """
        If a chunk's metadata does not contain a 'source' key,
        the source field defaults to 'unknown' rather than raising.
        """
        collection = MagicMock()
        collection.count.return_value = 1
        collection.query.return_value = {
            "documents": [["text without source"]],
            "metadatas": [[{}]],  # no 'source' key
            "distances": [[0.1]],
        }

        results = _retrieve_candidates(collection, [0.1], n=1)

        assert results[0]["source"] == "unknown"


# ---------------------------------------------------------------------------
# _rerank
# ---------------------------------------------------------------------------

class TestRerank:
    """Tests for the Cohere Rerank step."""

    def test_returns_top_n_chunks_in_relevance_order(self):
        """
        _rerank returns exactly top_n chunks, ordered by descending
        rerank relevance score, with the original chunk data preserved.
        """
        co = MagicMock()
        # Reranker swaps the order: chunk at index 1 is more relevant than chunk at 0
        co.rerank.return_value = MagicMock(
            results=[
                _make_rerank_result(index=1, score=0.95),
                _make_rerank_result(index=0, score=0.72),
            ]
        )

        result = _rerank(co, SAMPLE_COMPLAINT, SAMPLE_CHUNKS, top_n=2)

        assert len(result) == 2
        assert result[0]["source"] == SAMPLE_CHUNKS[1]["source"]  # index 1 first
        assert result[0]["rerank_score"] == 0.95
        assert result[1]["source"] == SAMPLE_CHUNKS[0]["source"]  # index 0 second

    def test_augments_chunk_with_rerank_score(self):
        """Each returned chunk must have a 'rerank_score' key added by _rerank."""
        co = MagicMock()
        co.rerank.return_value = MagicMock(
            results=[_make_rerank_result(index=0, score=0.88)]
        )

        result = _rerank(co, SAMPLE_COMPLAINT, SAMPLE_CHUNKS, top_n=1)

        assert "rerank_score" in result[0]
        assert result[0]["rerank_score"] == 0.88

    def test_calls_cohere_with_correct_model_and_documents(self):
        """
        _rerank calls co.rerank with the correct model name, the complaint
        as the query, and the chunk texts as the documents list.
        """
        co = MagicMock()
        co.rerank.return_value = MagicMock(
            results=[_make_rerank_result(index=0, score=0.9)]
        )

        _rerank(co, SAMPLE_COMPLAINT, SAMPLE_CHUNKS, top_n=1)

        co.rerank.assert_called_once_with(
            model="rerank-english-v3.0",
            query=SAMPLE_COMPLAINT,
            documents=[c["text"] for c in SAMPLE_CHUNKS],
            top_n=1,
        )

    def test_cohere_error_propagates(self):
        """If Cohere Rerank raises, the exception propagates to the caller."""
        co = MagicMock()
        co.rerank.side_effect = Exception("Rerank service unavailable")

        with pytest.raises(Exception, match="Rerank service unavailable"):
            _rerank(co, SAMPLE_COMPLAINT, SAMPLE_CHUNKS)


# ---------------------------------------------------------------------------
# _build_messages
# ---------------------------------------------------------------------------

class TestBuildMessages:
    """Tests for the prompt construction step."""

    def test_returns_two_strings(self):
        """_build_messages must return a (system_prompt, user_message) tuple of strings."""
        system_prompt, user_message = _build_messages(SAMPLE_COMPLAINT, SAMPLE_CHUNKS)
        assert isinstance(system_prompt, str)
        assert isinstance(user_message, str)

    def test_system_prompt_contains_key_analyst_rules(self):
        """
        The system prompt must contain the hard rules about citation,
        remedy prohibition, and draft-only status — these are the safety
        guardrails that prevent the model from producing harmful output.
        """
        system_prompt, _ = _build_messages(SAMPLE_COMPLAINT, SAMPLE_CHUNKS)
        assert "cite" in system_prompt.lower() or "source" in system_prompt.lower()
        assert "remedy" in system_prompt.lower() or "financial" in system_prompt.lower()
        assert "draft" in system_prompt.lower() or "review" in system_prompt.lower()

    def test_user_message_includes_complaint(self):
        """The complaint text must appear in the user message."""
        _, user_message = _build_messages(SAMPLE_COMPLAINT, SAMPLE_CHUNKS)
        assert SAMPLE_COMPLAINT in user_message

    def test_user_message_labels_each_chunk_with_source(self):
        """
        Each chunk must appear in the user message with its source filename
        as a label, so the model can cite specific documents.
        """
        _, user_message = _build_messages(SAMPLE_COMPLAINT, SAMPLE_CHUNKS)
        for chunk in SAMPLE_CHUNKS:
            assert chunk["source"] in user_message
            assert chunk["text"] in user_message

    def test_user_message_requests_json_output(self):
        """The user message must instruct the model to return a JSON object."""
        _, user_message = _build_messages(SAMPLE_COMPLAINT, SAMPLE_CHUNKS)
        assert "json" in user_message.lower()
        assert "failure_point" in user_message
        assert "confidence_score" in user_message

    def test_complaint_truncated_at_2000_chars(self):
        """
        A complaint longer than 2000 characters must be truncated in the
        user message to prevent token overflow. The truncation marker
        must be appended so the reviewer knows content was cut.
        """
        long_complaint = "A" * 3000
        _, user_message = _build_messages(long_complaint, SAMPLE_CHUNKS)
        assert "A" * 2000 in user_message
        assert "A" * 2001 not in user_message
        assert "truncated" in user_message.lower()

    def test_short_complaint_not_truncated(self):
        """A complaint under 2000 characters must appear verbatim in the message."""
        short_complaint = "Transfer of $100 is missing after 3 days."
        _, user_message = _build_messages(short_complaint, SAMPLE_CHUNKS)
        assert short_complaint in user_message
        assert "truncated" not in user_message.lower()


# ---------------------------------------------------------------------------
# _parse_model_output
# ---------------------------------------------------------------------------

class TestParseModelOutput:
    """Tests for the JSON parsing and normalisation step."""

    def test_parses_clean_json_response(self):
        """A clean JSON string from the model is parsed into a valid InvestigationResult."""
        raw = json.dumps(VALID_MODEL_JSON)
        result = _parse_model_output(raw, SAMPLE_CHUNKS)

        assert isinstance(result, InvestigationResult)
        assert result.failure_point == "institution"
        assert result.confidence_score == 0.85
        assert result.timeline_reconstruction == VALID_MODEL_JSON["timeline_reconstruction"]

    def test_extracts_json_from_markdown_fence(self):
        """
        If the model wraps its JSON in a ```json ... ``` fence (a common model
        behaviour despite instructions), the fence is stripped and JSON parsed.
        """
        raw = f"Here is my analysis:\n```json\n{json.dumps(VALID_MODEL_JSON)}\n```"
        result = _parse_model_output(raw, SAMPLE_CHUNKS)
        assert result.failure_point == "institution"

    def test_extracts_json_from_surrounding_prose(self):
        """
        If the model adds preamble text before the JSON object, the outermost
        {...} block is extracted and parsed.
        """
        raw = f"Sure, here is the result: {json.dumps(VALID_MODEL_JSON)} Thank you."
        result = _parse_model_output(raw, SAMPLE_CHUNKS)
        assert result.failure_point == "institution"

    def test_fallback_on_completely_unparseable_output(self):
        """
        When the model returns something that cannot be parsed as JSON at all,
        _parse_model_output returns a safe fallback result rather than raising,
        and sets escalation flags to alert the human reviewer.
        """
        raw = "I cannot generate a structured analysis for this complaint."
        result = _parse_model_output(raw, SAMPLE_CHUNKS)

        assert result.failure_point == "unknown"
        assert result.confidence_score == 0.0
        assert "model_output_parse_failure" in result.escalation_flags
        assert "manual_review_required" in result.escalation_flags

    def test_invalid_failure_point_normalised_to_unknown(self):
        """
        A failure_point value outside the allowed literals must be normalised
        to 'unknown' rather than causing a ValidationError at parse time.
        """
        data = {**VALID_MODEL_JSON, "failure_point": "third_party_vendor"}
        result = _parse_model_output(json.dumps(data), SAMPLE_CHUNKS)
        assert result.failure_point == "unknown"

    def test_confidence_score_above_1_clamped_to_1(self):
        """A model-returned confidence_score above 1.0 is clamped to exactly 1.0."""
        data = {**VALID_MODEL_JSON, "confidence_score": 1.8}
        result = _parse_model_output(json.dumps(data), SAMPLE_CHUNKS)
        assert result.confidence_score == 1.0

    def test_confidence_score_below_0_clamped_to_0(self):
        """A model-returned confidence_score below 0.0 is clamped to exactly 0.0."""
        data = {**VALID_MODEL_JSON, "confidence_score": -0.5}
        result = _parse_model_output(json.dumps(data), SAMPLE_CHUNKS)
        assert result.confidence_score == 0.0

    def test_sources_derived_from_chunks_not_model_output(self):
        """
        The sources list must come from the chunk metadata, not from anything
        the model says — this ensures citations are grounded in retrieved docs.
        """
        result = _parse_model_output(json.dumps(VALID_MODEL_JSON), SAMPLE_CHUNKS)
        expected = sorted({"transfer_timelines.txt", "institutional_transfer_process.txt"})
        assert result.sources == expected

    def test_sources_are_deduplicated_and_sorted(self):
        """
        If multiple chunks share the same source document, the source filename
        must appear only once in the result, and the list must be sorted.
        """
        duplicate_chunks = [
            {**SAMPLE_CHUNKS[0]},
            {**SAMPLE_CHUNKS[0], "text": "another chunk from the same file"},
        ]
        result = _parse_model_output(json.dumps(VALID_MODEL_JSON), duplicate_chunks)
        assert result.sources.count("transfer_timelines.txt") == 1

    def test_escalation_flags_parsed_as_list_of_strings(self):
        """A non-empty escalation_flags list from the model is preserved correctly."""
        data = {**VALID_MODEL_JSON, "escalation_flags": ["potential_fraud", "large_transaction_review"]}
        result = _parse_model_output(json.dumps(data), SAMPLE_CHUNKS)
        assert result.escalation_flags == ["potential_fraud", "large_transaction_review"]

    def test_empty_escalation_flags_preserved(self):
        """An empty escalation_flags list is returned as an empty list, not None."""
        data = {**VALID_MODEL_JSON, "escalation_flags": []}
        result = _parse_model_output(json.dumps(data), SAMPLE_CHUNKS)
        assert result.escalation_flags == []

    def test_non_castable_confidence_score_defaults_to_half(self):
        """If confidence_score cannot be cast to float, it defaults to 0.5."""
        data = {**VALID_MODEL_JSON, "confidence_score": "high"}
        result = _parse_model_output(json.dumps(data), SAMPLE_CHUNKS)
        assert result.confidence_score == 0.5


# ---------------------------------------------------------------------------
# investigate (full pipeline orchestration)
# ---------------------------------------------------------------------------

class TestInvestigate:
    """Integration-style tests for the full investigation pipeline."""

    def _mock_co(self) -> MagicMock:
        """Return a Cohere mock pre-configured for the happy path."""
        co = MagicMock()
        co.embed.return_value = _make_embed_response()
        co.rerank.return_value = MagicMock(
            results=[
                _make_rerank_result(index=0, score=0.95),
                _make_rerank_result(index=1, score=0.88),
            ]
        )
        co.chat.return_value = MagicMock(text=json.dumps(VALID_MODEL_JSON))
        return co

    async def test_happy_path_returns_investigation_result(self):
        """
        Given mocked Cohere and ChromaDB clients, investigate() must return
        a fully populated InvestigationResult with the expected field values.
        """
        mock_co = self._mock_co()
        mock_collection = _make_mock_collection()

        with patch("app.query._build_cohere_client", return_value=mock_co), \
             patch("app.query._build_chroma_collection", return_value=mock_collection):
            result = await investigate(SAMPLE_COMPLAINT)

        assert isinstance(result, InvestigationResult)
        assert result.failure_point == "institution"
        assert result.confidence_score == 0.85
        assert len(result.sources) > 0

    async def test_pipeline_calls_each_stage_in_order(self):
        """
        embed → retrieve → rerank → chat must all be called exactly once,
        confirming that no stage is accidentally skipped.
        """
        mock_co = self._mock_co()
        mock_collection = _make_mock_collection()

        with patch("app.query._build_cohere_client", return_value=mock_co), \
             patch("app.query._build_chroma_collection", return_value=mock_collection):
            await investigate(SAMPLE_COMPLAINT)

        mock_co.embed.assert_called_once()
        mock_collection.query.assert_called_once()
        mock_co.rerank.assert_called_once()
        mock_co.chat.assert_called_once()

    async def test_raises_environment_error_on_missing_api_key(self, monkeypatch):
        """
        If COHERE_API_KEY is absent, investigate() must raise EnvironmentError
        before any retrieval or model call is made.
        """
        monkeypatch.delenv("COHERE_API_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="COHERE_API_KEY"):
            await investigate(SAMPLE_COMPLAINT)

    async def test_raises_runtime_error_when_collection_missing(self, monkeypatch):
        """
        If the ChromaDB collection has not been created (ingest not yet run),
        investigate() must raise a RuntimeError with a clear remediation message.
        """
        monkeypatch.setenv("COHERE_API_KEY", "test-key")
        mock_client = MagicMock()
        mock_client.get_collection.side_effect = Exception("not found")

        with patch("app.query.cohere.Client"), \
             patch("app.query.chromadb.PersistentClient", return_value=mock_client):
            with pytest.raises(RuntimeError, match="python -m app.ingest"):
                await investigate(SAMPLE_COMPLAINT)

    async def test_unparseable_model_response_returns_fallback_not_raise(self):
        """
        If Command R+ returns something that cannot be parsed as JSON,
        investigate() must return a safe fallback InvestigationResult rather
        than propagating a parse error to the caller.
        """
        mock_co = self._mock_co()
        mock_co.chat.return_value = MagicMock(
            text="Sorry, I cannot help with that request."
        )
        mock_collection = _make_mock_collection()

        with patch("app.query._build_cohere_client", return_value=mock_co), \
             patch("app.query._build_chroma_collection", return_value=mock_collection):
            result = await investigate(SAMPLE_COMPLAINT)

        assert result.failure_point == "unknown"
        assert "model_output_parse_failure" in result.escalation_flags

    async def test_cohere_embed_error_propagates(self):
        """If the embed call fails, investigate() propagates the exception."""
        mock_co = self._mock_co()
        mock_co.embed.side_effect = Exception("embed service down")
        mock_collection = _make_mock_collection()

        with patch("app.query._build_cohere_client", return_value=mock_co), \
             patch("app.query._build_chroma_collection", return_value=mock_collection):
            with pytest.raises(Exception, match="embed service down"):
                await investigate(SAMPLE_COMPLAINT)


# ---------------------------------------------------------------------------
# run_investigation (route adapter)
# ---------------------------------------------------------------------------

class TestRunInvestigation:
    """Tests for the thin route adapter that wraps investigate()."""

    async def test_delegates_complaint_to_investigate(self):
        """
        run_investigation must extract the complaint string from the request
        and pass it to investigate(), returning whatever investigate() returns.
        """
        request = InvestigateRequest(complaint=SAMPLE_COMPLAINT)
        expected = InvestigationResult(
            timeline_reconstruction="Timeline.",
            failure_point="client",
            draft_client_response="Draft.\n\nAGENT MUST VERIFY: nothing.",
            confidence_score=0.6,
        )

        with patch("app.query.investigate", return_value=expected) as mock_inv:
            result = await run_investigation(request)

        mock_inv.assert_called_once_with(SAMPLE_COMPLAINT)
        assert result is expected


# ---------------------------------------------------------------------------
# HTTP endpoints (via FastAPI TestClient)
# ---------------------------------------------------------------------------

class TestHTTPEndpoints:
    """Black-box tests for the FastAPI routes via the TestClient."""

    def test_post_investigate_returns_422_for_missing_body(self):
        """POST /investigate with no body must return 422 Unprocessable Entity."""
        client = TestClient(app)
        response = client.post("/investigate", json={})
        assert response.status_code == 422

    def test_post_investigate_returns_422_for_short_complaint(self):
        """
        POST /investigate with a complaint shorter than 10 characters must
        return 422 — Pydantic's min_length validation rejects it before the
        pipeline is invoked.
        """
        client = TestClient(app)
        response = client.post("/investigate", json={"complaint": "too short"})
        assert response.status_code == 422

    def test_post_investigate_happy_path_returns_200(self):
        """
        POST /investigate with a valid complaint returns 200 and a response
        body that conforms to the InvestigationResult schema.
        """
        mock_co = MagicMock()
        mock_co.embed.return_value = _make_embed_response()
        mock_co.rerank.return_value = MagicMock(
            results=[_make_rerank_result(index=0, score=0.9)]
        )
        mock_co.chat.return_value = MagicMock(text=json.dumps(VALID_MODEL_JSON))

        mock_collection = _make_mock_collection(count=1)
        mock_collection.query.return_value = {
            "documents": [["Some chunk text."]],
            "metadatas": [[{"source": "transfer_timelines.txt"}]],
            "distances": [[0.1]],
        }

        client = TestClient(app)

        with patch("app.query._build_cohere_client", return_value=mock_co), \
             patch("app.query._build_chroma_collection", return_value=mock_collection):
            response = client.post(
                "/investigate",
                json={"complaint": SAMPLE_COMPLAINT},
            )

        assert response.status_code == 200
        body = response.json()
        result = InvestigationResult(**body)
        assert result.failure_point in {"wealthsimple", "institution", "client", "unknown"}
        assert 0.0 <= result.confidence_score <= 1.0

    def test_post_ingest_returns_200(self):
        """
        POST /ingest with all dependencies mocked returns 200 and an
        IngestResponse with a boolean success field.
        """
        mock_co = MagicMock()
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}
        mock_collection.upsert.return_value = None

        def embed_side_effect(**kwargs):
            mock = MagicMock()
            mock.embeddings = [[0.1] for _ in range(len(kwargs["texts"]))]
            return mock

        mock_co.embed.side_effect = embed_side_effect

        client = TestClient(app)

        with patch("app.ingest._get_cohere_client", return_value=mock_co), \
             patch("app.ingest._get_chroma_collection", return_value=mock_collection):
            response = client.post("/ingest")

        assert response.status_code == 200
        body = response.json()
        assert "success" in body
        assert isinstance(body["success"], bool)
        assert "documents_ingested" in body
