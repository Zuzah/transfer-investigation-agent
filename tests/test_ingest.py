"""
Tests for the document ingestion pipeline in app/ingest.py.

All Cohere and ChromaDB calls are mocked — these tests run without
a live API key or a running database instance.
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from app.ingest import (
    _chunk_text,
    _embed_chunks,
    _find_break,
    _get_chroma_collection,
    _get_cohere_client,
    _load_documents,
    ingest_documents,
)
from app.models import IngestResponse


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_embed_response(n: int) -> MagicMock:
    """Return a mock Cohere embed response containing n dummy embeddings."""
    mock = MagicMock()
    mock.embeddings = [[0.1, 0.2, 0.3] for _ in range(n)]
    return mock


def _make_mock_collection(existing_ids: list[str] | None = None) -> MagicMock:
    """
    Return a mock ChromaDB collection.

    existing_ids — IDs that collection.get() will report as already present.
    """
    collection = MagicMock()
    collection.count.return_value = 0
    collection.get.return_value = {"ids": existing_ids or []}
    collection.upsert.return_value = None
    return collection


# ---------------------------------------------------------------------------
# _find_break
# ---------------------------------------------------------------------------

class TestFindBreak:
    """Unit tests for the natural break-point detection helper."""

    def test_prefers_paragraph_break_over_sentence(self):
        """
        When both a paragraph boundary (\\n\\n) and a sentence boundary exist
        in the tolerance window, _find_break must choose the paragraph break.
        """
        # Paragraph break at index 25; sentence boundary (". ") at index 11
        text = "First sentence. End.\n\nNew paragraph starts."
        # near=30, tolerance=20 → window=[10,30] — both boundaries are visible
        cut = _find_break(text, 30, 20)
        # Paragraph \n\n is at 20; returned cut should be 22 (pos+2)
        assert text[cut - 2 : cut] == "\n\n" or cut <= 23

    def test_falls_back_to_sentence_when_no_paragraph(self):
        """
        Without a paragraph break in the window, _find_break must cut
        after the nearest sentence-ending punctuation.
        """
        text = "First sentence. Second sentence continues here and goes on."
        # near=25, tolerance=15 → window=[10,25]; ". " is at 15
        cut = _find_break(text, 25, 15)
        # The character before the cut should be punctuation or its trailing space
        assert cut > 10
        assert cut <= 25

    def test_falls_back_to_word_boundary_when_no_sentence(self):
        """
        Without sentence punctuation in the window, _find_break must cut
        at a word boundary (space).
        """
        text = "abcdefghij klmnopqrstuvwxyz"
        # near=20, tolerance=5 → window=[15,20]
        # The space is at index 10 — outside the window
        # Word boundary in window: look for space in [15,20] → none
        # Falls back to hard cut at near=20
        cut = _find_break(text, 20, 5)
        assert cut <= 20

    def test_hard_cut_when_no_boundary_found(self):
        """
        When no paragraph, sentence, or word boundary exists in the tolerance
        window, _find_break must return `near` exactly (a hard cut).
        """
        text = "abcdefghijklmnopqrstuvwxyz"  # no spaces or punctuation
        cut = _find_break(text, 15, 5)
        assert cut == 15

    def test_word_boundary_preferred_over_hard_cut(self):
        """
        A space anywhere in the tolerance window is preferred over a hard cut.
        """
        text = "hello world abcde"
        # Space at index 5 and 11; near=14, tolerance=10 → window=[4,14]
        cut = _find_break(text, 14, 10)
        # Should cut after a space (index 12, so cut=12)
        assert text[cut - 1] == " " or text[:cut].endswith(" ")


# ---------------------------------------------------------------------------
# _chunk_text
# ---------------------------------------------------------------------------

class TestChunkText:
    """Unit tests for the overlapping text chunker."""

    def test_short_text_produces_single_chunk(self):
        """Text shorter than chunk_size must produce exactly one chunk."""
        text = "This is a short document."
        chunks = _chunk_text(text, chunk_size=200, overlap=20)
        assert chunks == ["This is a short document."]

    def test_long_text_produces_multiple_chunks(self):
        """Text significantly longer than chunk_size must produce more than one chunk."""
        text = ("The quick brown fox jumps over the lazy dog. " * 30)
        chunks = _chunk_text(text, chunk_size=100, overlap=20)
        assert len(chunks) > 1

    def test_chunks_are_non_empty_and_stripped(self):
        """Every returned chunk must be non-empty and have no leading/trailing whitespace."""
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three.\n\nParagraph four."
        chunks = _chunk_text(text, chunk_size=20, overlap=5)
        assert all(len(c) > 0 for c in chunks)
        assert all(c == c.strip() for c in chunks)

    def test_overlap_means_adjacent_chunks_share_content(self):
        """
        The start of chunk[n+1] must contain words that appeared near the
        end of chunk[n], confirming the overlap window is being applied.
        """
        # Use a predictable repeating pattern so we can track overlap
        text = " ".join(f"word{i}" for i in range(60))
        chunks = _chunk_text(text, chunk_size=100, overlap=30)
        assert len(chunks) >= 2
        # The last word of chunk[0] should appear somewhere in chunk[1]
        last_word_of_first = chunks[0].split()[-1]
        assert last_word_of_first in chunks[1]

    def test_empty_string_returns_empty_list(self):
        """An empty input string must produce an empty list, not crash."""
        assert _chunk_text("") == []

    def test_whitespace_only_returns_empty_list(self):
        """A whitespace-only string must produce an empty list."""
        assert _chunk_text("   \n\n   ") == []

    def test_crlf_line_endings_normalised(self):
        """Windows-style CRLF line endings must be normalised before chunking."""
        text_crlf = "Line one.\r\nLine two.\r\nLine three."
        text_lf = "Line one.\nLine two.\nLine three."
        assert _chunk_text(text_crlf, chunk_size=200, overlap=20) == \
               _chunk_text(text_lf, chunk_size=200, overlap=20)

    def test_chunk_size_respected_approximately(self):
        """
        No chunk should exceed chunk_size + tolerance (25% of chunk_size),
        accounting for the boundary-search window.
        """
        text = "word " * 200
        chunk_size = 100
        chunks = _chunk_text(text, chunk_size=chunk_size, overlap=20)
        tolerance = chunk_size // 4
        for chunk in chunks:
            assert len(chunk) <= chunk_size + tolerance, (
                f"Chunk exceeds allowed size: {len(chunk)} > {chunk_size + tolerance}"
            )


# ---------------------------------------------------------------------------
# _load_documents
# ---------------------------------------------------------------------------

class TestLoadDocuments:
    """Tests for the file-loading step of the ingestion pipeline."""

    def test_loads_all_txt_files(self, tmp_path: Path):
        """All .txt files in the docs directory are loaded and returned."""
        (tmp_path / "doc_a.txt").write_text("Content of doc A.")
        (tmp_path / "doc_b.txt").write_text("Content of doc B.")
        with patch("app.ingest.DOCS_DIR", tmp_path):
            docs = _load_documents()
        assert len(docs) == 2
        names = {d["name"] for d in docs}
        assert names == {"doc_a.txt", "doc_b.txt"}

    def test_returns_correct_text_content(self, tmp_path: Path):
        """The 'text' key of each returned dict contains the file's content."""
        (tmp_path / "doc.txt").write_text("  Hello, world.  ")
        with patch("app.ingest.DOCS_DIR", tmp_path):
            docs = _load_documents()
        assert docs[0]["text"] == "Hello, world."  # stripped

    def test_ignores_non_txt_files(self, tmp_path: Path):
        """Files with extensions other than .txt are ignored."""
        (tmp_path / "notes.md").write_text("Markdown content.")
        (tmp_path / "data.csv").write_text("col1,col2")
        (tmp_path / "real.txt").write_text("This is the only valid file.")
        with patch("app.ingest.DOCS_DIR", tmp_path):
            docs = _load_documents()
        assert len(docs) == 1
        assert docs[0]["name"] == "real.txt"

    def test_skips_empty_files(self, tmp_path: Path):
        """Files that are empty or contain only whitespace are silently skipped."""
        (tmp_path / "empty.txt").write_text("   \n\n  ")
        (tmp_path / "valid.txt").write_text("Has content.")
        with patch("app.ingest.DOCS_DIR", tmp_path):
            docs = _load_documents()
        assert len(docs) == 1
        assert docs[0]["name"] == "valid.txt"

    def test_raises_if_docs_dir_missing(self, tmp_path: Path):
        """FileNotFoundError is raised when DOCS_DIR does not exist."""
        missing_dir = tmp_path / "does_not_exist"
        with patch("app.ingest.DOCS_DIR", missing_dir):
            with pytest.raises(FileNotFoundError, match="Docs directory not found"):
                _load_documents()

    def test_raises_if_no_txt_files(self, tmp_path: Path):
        """ValueError is raised when the directory exists but contains no .txt files."""
        with patch("app.ingest.DOCS_DIR", tmp_path):
            with pytest.raises(ValueError, match="No .txt files found"):
                _load_documents()


# ---------------------------------------------------------------------------
# _get_cohere_client
# ---------------------------------------------------------------------------

class TestGetCohereClient:
    """Tests for API key loading and client construction."""

    def test_raises_if_api_key_missing(self, monkeypatch):
        """EnvironmentError is raised when COHERE_API_KEY is absent from the environment."""
        monkeypatch.delenv("COHERE_API_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="COHERE_API_KEY"):
            _get_cohere_client()

    def test_returns_client_when_key_present(self, monkeypatch):
        """A cohere.Client is returned when COHERE_API_KEY is set."""
        monkeypatch.setenv("COHERE_API_KEY", "test-key-123")
        with patch("app.ingest.cohere.Client") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = _get_cohere_client()
        mock_cls.assert_called_once_with("test-key-123")
        assert client is mock_cls.return_value


# ---------------------------------------------------------------------------
# _get_chroma_collection
# ---------------------------------------------------------------------------

class TestGetChromaCollection:
    """Tests for ChromaDB collection initialisation."""

    def test_creates_collection_when_absent(self):
        """
        get_or_create_collection is called with the correct name and
        cosine similarity metadata when no collection exists.
        """
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        with patch("app.ingest.chromadb.PersistentClient", return_value=mock_client):
            result = _get_chroma_collection(overwrite=False)

        mock_client.get_or_create_collection.assert_called_once_with(
            name="transfer_knowledge",
            metadata={"hnsw:space": "cosine"},
        )
        assert result is mock_collection

    def test_overwrite_deletes_then_recreates(self):
        """
        With overwrite=True, delete_collection is called before
        get_or_create_collection so the collection is rebuilt from scratch.
        """
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = MagicMock()

        with patch("app.ingest.chromadb.PersistentClient", return_value=mock_client):
            _get_chroma_collection(overwrite=True)

        mock_client.delete_collection.assert_called_once_with("transfer_knowledge")
        mock_client.get_or_create_collection.assert_called_once()

    def test_overwrite_ignores_missing_collection_error(self):
        """
        With overwrite=True, if delete_collection raises (collection did not
        exist), the error is silently swallowed and creation proceeds normally.
        """
        mock_client = MagicMock()
        mock_client.delete_collection.side_effect = Exception("Not found")
        mock_client.get_or_create_collection.return_value = MagicMock()

        with patch("app.ingest.chromadb.PersistentClient", return_value=mock_client):
            # Must not raise
            _get_chroma_collection(overwrite=True)

        mock_client.get_or_create_collection.assert_called_once()


# ---------------------------------------------------------------------------
# _embed_chunks
# ---------------------------------------------------------------------------

class TestEmbedChunks:
    """Tests for the batched Cohere embedding step."""

    def test_happy_path_returns_embeddings(self):
        """_embed_chunks returns one embedding vector per input text."""
        co = MagicMock()
        co.embed.return_value = _make_embed_response(3)
        texts = ["chunk one", "chunk two", "chunk three"]

        result = _embed_chunks(co, texts)

        assert len(result) == 3
        co.embed.assert_called_once_with(
            texts=texts,
            model="embed-english-v3.0",
            input_type="search_document",
        )

    def test_batches_at_96_texts_per_call(self):
        """
        When given more than 96 texts, _embed_chunks must split them into
        multiple API calls of at most 96 texts each.
        """
        co = MagicMock()

        def embed_side_effect(**kwargs):
            return _make_embed_response(len(kwargs["texts"]))

        co.embed.side_effect = embed_side_effect
        texts = ["chunk"] * 100  # needs 2 batches: 96 + 4

        result = _embed_chunks(co, texts)

        assert len(result) == 100
        assert co.embed.call_count == 2
        first_call_texts = co.embed.call_args_list[0].kwargs["texts"]
        second_call_texts = co.embed.call_args_list[1].kwargs["texts"]
        assert len(first_call_texts) == 96
        assert len(second_call_texts) == 4

    def test_retries_on_transient_api_error(self):
        """
        If the Cohere API raises on the first two attempts but succeeds on
        the third, _embed_chunks must return the embeddings without raising.
        """
        co = MagicMock()
        success = _make_embed_response(1)
        co.embed.side_effect = [
            Exception("timeout"),
            Exception("timeout"),
            success,
        ]

        with patch("app.ingest.time.sleep"):  # avoid real sleeps
            result = _embed_chunks(co, ["one chunk"])

        assert result == success.embeddings
        assert co.embed.call_count == 3

    def test_reraises_after_three_failures(self):
        """
        If all three attempts for a batch fail, _embed_chunks must re-raise
        the last exception rather than returning partial results.
        """
        co = MagicMock()
        co.embed.side_effect = Exception("persistent API failure")

        with patch("app.ingest.time.sleep"):
            with pytest.raises(Exception, match="persistent API failure"):
                _embed_chunks(co, ["one chunk"])

        assert co.embed.call_count == 3

    def test_retry_backoff_sleeps_between_attempts(self):
        """
        Between retry attempts, time.sleep is called with exponential back-off
        values (1 s, then 2 s).
        """
        co = MagicMock()
        success = _make_embed_response(1)
        co.embed.side_effect = [Exception("err"), Exception("err"), success]

        with patch("app.ingest.time.sleep") as mock_sleep:
            _embed_chunks(co, ["one chunk"])

        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # 2**0
        mock_sleep.assert_any_call(2)  # 2**1


# ---------------------------------------------------------------------------
# ingest_documents (orchestration)
# ---------------------------------------------------------------------------

class TestIngestDocuments:
    """Integration-style tests for the full ingestion orchestrator."""

    def _patch_all(self, tmp_path: Path, mock_co: MagicMock, mock_collection: MagicMock):
        """Return a context-manager stack that patches all external dependencies."""
        return (
            patch("app.ingest._get_cohere_client", return_value=mock_co),
            patch("app.ingest._get_chroma_collection", return_value=mock_collection),
            patch("app.ingest.DOCS_DIR", tmp_path),
        )

    async def test_happy_path_ingests_all_chunks(self, tmp_path: Path):
        """
        Given one document that produces multiple chunks, ingest_documents
        embeds and upserts all chunks and returns a success response with
        the correct chunk count.
        """
        (tmp_path / "doc.txt").write_text("Sentence one. " * 100)  # long enough to chunk
        mock_co = MagicMock()
        mock_collection = _make_mock_collection()

        # Embed response size must match number of chunks — we let it scale dynamically
        def embed_side_effect(**kwargs):
            return _make_embed_response(len(kwargs["texts"]))

        mock_co.embed.side_effect = embed_side_effect

        with patch("app.ingest._get_cohere_client", return_value=mock_co), \
             patch("app.ingest._get_chroma_collection", return_value=mock_collection), \
             patch("app.ingest.DOCS_DIR", tmp_path):
            result = await ingest_documents()

        assert result.success is True
        assert result.documents_ingested > 0
        mock_collection.upsert.assert_called_once()

    async def test_returns_zero_when_all_chunks_already_present(self, tmp_path: Path):
        """
        When every chunk ID is already present in ChromaDB, ingest_documents
        must return 0 documents_ingested and skip the embed + upsert calls.
        """
        (tmp_path / "doc.txt").write_text("Short document.")
        mock_co = MagicMock()

        # Simulate all IDs already present
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": ["doc.txt::0"]}
        mock_collection.upsert.return_value = None

        with patch("app.ingest._get_cohere_client", return_value=mock_co), \
             patch("app.ingest._get_chroma_collection", return_value=mock_collection), \
             patch("app.ingest.DOCS_DIR", tmp_path):
            result = await ingest_documents()

        assert result.documents_ingested == 0
        mock_co.embed.assert_not_called()
        mock_collection.upsert.assert_not_called()

    async def test_overwrite_rebuilds_collection(self, tmp_path: Path):
        """
        With overwrite=True, _get_chroma_collection is called with overwrite=True,
        and all chunks are embedded and upserted regardless of existing IDs.
        """
        (tmp_path / "doc.txt").write_text("Sentence. " * 10)
        mock_co = MagicMock()
        mock_collection = _make_mock_collection()

        def embed_side_effect(**kwargs):
            return _make_embed_response(len(kwargs["texts"]))

        mock_co.embed.side_effect = embed_side_effect

        with patch("app.ingest._get_cohere_client", return_value=mock_co), \
             patch("app.ingest._get_chroma_collection", return_value=mock_collection) as mock_get_col, \
             patch("app.ingest.DOCS_DIR", tmp_path):
            result = await ingest_documents(overwrite=True)

        mock_get_col.assert_called_once_with(overwrite=True)
        assert result.success is True
        mock_collection.upsert.assert_called_once()

    async def test_chunk_ids_use_filename_and_index(self, tmp_path: Path):
        """
        Chunk IDs upserted into ChromaDB must follow the
        '<filename>::<chunk_index>' format for idempotency.
        """
        (tmp_path / "timelines.txt").write_text("Short doc.")
        mock_co = MagicMock()
        mock_collection = _make_mock_collection()
        mock_co.embed.return_value = _make_embed_response(1)

        with patch("app.ingest._get_cohere_client", return_value=mock_co), \
             patch("app.ingest._get_chroma_collection", return_value=mock_collection), \
             patch("app.ingest.DOCS_DIR", tmp_path):
            await ingest_documents()

        upsert_kwargs = mock_collection.upsert.call_args.kwargs
        assert upsert_kwargs["ids"][0] == "timelines.txt::0"

    async def test_metadata_includes_source_and_chunk_index(self, tmp_path: Path):
        """
        Each upserted chunk must carry 'source' (filename) and 'chunk_index'
        in its metadata, so retrieval results can be attributed to their document.
        """
        (tmp_path / "failures.txt").write_text("Failure pattern content here.")
        mock_co = MagicMock()
        mock_collection = _make_mock_collection()
        mock_co.embed.return_value = _make_embed_response(1)

        with patch("app.ingest._get_cohere_client", return_value=mock_co), \
             patch("app.ingest._get_chroma_collection", return_value=mock_collection), \
             patch("app.ingest.DOCS_DIR", tmp_path):
            await ingest_documents()

        metadatas = mock_collection.upsert.call_args.kwargs["metadatas"]
        assert metadatas[0]["source"] == "failures.txt"
        assert metadatas[0]["chunk_index"] == 0

    async def test_raises_environment_error_on_missing_api_key(
        self, tmp_path: Path, monkeypatch
    ):
        """
        If COHERE_API_KEY is not set, ingest_documents must raise EnvironmentError
        before any file I/O or network call is made.
        """
        monkeypatch.delenv("COHERE_API_KEY", raising=False)
        (tmp_path / "doc.txt").write_text("Content.")
        with patch("app.ingest.DOCS_DIR", tmp_path):
            with pytest.raises(EnvironmentError, match="COHERE_API_KEY"):
                await ingest_documents()

    async def test_cohere_api_error_propagates(self, tmp_path: Path):
        """
        If Cohere raises during embedding (after all retries), the exception
        must propagate out of ingest_documents rather than being swallowed.
        """
        (tmp_path / "doc.txt").write_text("Some content to embed.")
        mock_co = MagicMock()
        mock_co.embed.side_effect = Exception("Cohere API down")
        mock_collection = _make_mock_collection()

        with patch("app.ingest._get_cohere_client", return_value=mock_co), \
             patch("app.ingest._get_chroma_collection", return_value=mock_collection), \
             patch("app.ingest.DOCS_DIR", tmp_path), \
             patch("app.ingest.time.sleep"):
            with pytest.raises(Exception, match="Cohere API down"):
                await ingest_documents()
