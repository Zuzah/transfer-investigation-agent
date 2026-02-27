"""
Document ingestion pipeline for the Transfer Investigation Agent.

Responsibilities:
  1. Read all .txt files from knowledge_base/docs/
  2. Chunk each document into ~300-token segments with ~50-token overlap
  3. Embed chunks using Cohere Embed v3 (embed-english-v3.0)
  4. Upsert chunks + embeddings into a ChromaDB collection persisted to ./chroma_db/

Configuration is read from environment variables via python-dotenv (see .env.example).

CLI usage:
    python -m app.ingest               # skip chunks already in the collection
    python -m app.ingest --overwrite   # delete collection and rebuild from scratch
"""

import argparse
import os
import sys
import time
from pathlib import Path

import chromadb
import cohere
from dotenv import load_dotenv

from app.models import IngestResponse

load_dotenv()

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

DOCS_DIR = Path(__file__).parent.parent / "knowledge_base" / "docs"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME = "transfer_knowledge"

# Token-to-character approximation for English text (1 token ≈ 4 chars).
# Targets: 300-token chunks with 50-token overlap.
CHUNK_TARGET_CHARS = 1_200   # ≈ 300 tokens
OVERLAP_CHARS = 200          # ≈ 50 tokens

# Cohere's embed endpoint accepts at most 96 texts per request.
COHERE_EMBED_BATCH_SIZE = 96


# ---------------------------------------------------------------------------
# Client initialisation
# ---------------------------------------------------------------------------

def _get_cohere_client() -> cohere.Client:
    """
    Load COHERE_API_KEY from the environment and return a configured Cohere client.

    Raises:
        EnvironmentError: If COHERE_API_KEY is not set.
    """
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "COHERE_API_KEY is not set. "
            "Copy .env.example to .env and add your Cohere API key."
        )
    return cohere.Client(api_key)


def _get_chroma_collection(overwrite: bool = False) -> chromadb.Collection:
    """
    Return the ChromaDB collection, creating it if necessary.

    The collection is persisted to CHROMA_DIR so embeddings survive restarts.
    Cosine similarity is used as the distance metric.

    Args:
        overwrite: If True, deletes the existing collection before recreating it.

    Returns:
        A ChromaDB Collection object ready for upsert and query operations.
    """
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if overwrite:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"[chroma] Existing collection '{COLLECTION_NAME}' deleted.")
        except Exception:
            pass  # Collection didn't exist yet — fine to continue.

    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Document loading
# ---------------------------------------------------------------------------

def _load_documents() -> list[dict]:
    """
    Load all .txt files from DOCS_DIR.

    Returns:
        List of dicts, each with:
          - 'name' (str): The filename, e.g. "transfer_timelines.txt"
          - 'text' (str): Full file content, stripped of leading/trailing whitespace

    Raises:
        FileNotFoundError: If DOCS_DIR does not exist.
        ValueError: If no .txt files are found in DOCS_DIR.
    """
    if not DOCS_DIR.exists():
        raise FileNotFoundError(
            f"Docs directory not found: {DOCS_DIR}\n"
            "Create the directory and add .txt process documents before ingesting."
        )

    txt_files = sorted(DOCS_DIR.glob("*.txt"))
    if not txt_files:
        raise ValueError(
            f"No .txt files found in {DOCS_DIR}.\n"
            "Add process documents before running ingestion."
        )

    documents = []
    for path in txt_files:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            print(f"[load]   Skipping empty file: {path.name}")
            continue
        documents.append({"name": path.name, "text": text})
        print(f"[load]   Loaded: {path.name} ({len(text):,} chars)")

    return documents


# ---------------------------------------------------------------------------
# Text chunking
# ---------------------------------------------------------------------------

def _find_break(text: str, near: int, tolerance: int) -> int:
    """
    Find the best natural break point in `text` near position `near`.

    Search order (highest preference first):
      1. Paragraph boundary (double newline) within [near - tolerance, near]
      2. Sentence-ending punctuation (. ! ?) followed by whitespace
      3. Word boundary (space)
      4. Hard cut at `near` if no boundary is found

    Args:
        text: The full document text.
        near: The target cut position (upper bound of the search window).
        tolerance: How far back from `near` to search for a boundary.

    Returns:
        The recommended cut position (exclusive end index for slicing).
    """
    window_start = max(0, near - tolerance)

    # 1. Paragraph break
    pos = text.rfind("\n\n", window_start, near)
    if pos != -1:
        return pos + 2  # include the blank line in the preceding chunk

    # 2. Sentence boundary: punctuation followed by space or newline
    best_sentence = -1
    for punct in (".\n", "!\n", "?\n", ". ", "! ", "? "):
        pos = text.rfind(punct, window_start, near)
        if pos > best_sentence:
            best_sentence = pos
    if best_sentence != -1:
        return best_sentence + 2  # include punctuation + delimiter

    # 3. Word boundary
    pos = text.rfind(" ", window_start, near)
    if pos != -1:
        return pos + 1

    # 4. Hard cut — no natural boundary found
    return near


def _chunk_text(
    text: str,
    chunk_size: int = CHUNK_TARGET_CHARS,
    overlap: int = OVERLAP_CHARS,
) -> list[str]:
    """
    Split text into overlapping chunks of approximately `chunk_size` characters.

    Each chunk preferentially ends at a paragraph or sentence boundary so that
    no chunk cuts mid-sentence. The `overlap` parameter carries characters from
    the end of one chunk into the beginning of the next, providing context
    continuity when the embedding model retrieves adjacent chunks.

    Args:
        text: The full document text.
        chunk_size: Target maximum size of each chunk in characters (≈300 tokens).
        overlap: Characters to carry over from the end of each chunk (≈50 tokens).

    Returns:
        List of non-empty text chunk strings.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    tolerance = chunk_size // 4  # 25% search window for natural break

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        cut = _find_break(text, end, tolerance)

        # Safety: always advance at least one character to prevent infinite loops.
        if cut <= start:
            cut = end

        chunk = text[start:cut].strip()
        if chunk:
            chunks.append(chunk)

        # Next chunk starts `overlap` characters before the cut point.
        start = max(start + 1, cut - overlap)

    return chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def _embed_chunks(co: cohere.Client, texts: list[str]) -> list[list[float]]:
    """
    Embed a list of text strings using Cohere Embed v3.

    Batches requests automatically to stay within Cohere's per-request limit.
    Retries each batch up to 3 times with exponential back-off on transient errors.

    Args:
        co: Authenticated Cohere client.
        texts: Chunk strings to embed.

    Returns:
        Flat list of embedding vectors in the same order as `texts`.

    Raises:
        Exception: Re-raises the last exception after 3 failed attempts.
    """
    embeddings: list[list[float]] = []
    total_batches = (len(texts) + COHERE_EMBED_BATCH_SIZE - 1) // COHERE_EMBED_BATCH_SIZE

    for batch_num, batch_start in enumerate(
        range(0, len(texts), COHERE_EMBED_BATCH_SIZE), start=1
    ):
        batch = texts[batch_start : batch_start + COHERE_EMBED_BATCH_SIZE]
        print(f"  [embed] Batch {batch_num}/{total_batches} — {len(batch)} chunk(s)...")

        for attempt in range(3):
            try:
                response = co.embed(
                    texts=batch,
                    model="embed-english-v3.0",
                    input_type="search_document",
                )
                embeddings.extend(response.embeddings)
                break
            except Exception as exc:
                if attempt == 2:
                    raise
                wait = 2**attempt  # 1 s, then 2 s
                print(
                    f"  [embed] API error (attempt {attempt + 1}/3): {exc}. "
                    f"Retrying in {wait}s..."
                )
                time.sleep(wait)

    return embeddings


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def ingest_documents(overwrite: bool = False) -> IngestResponse:
    """
    Run the full ingestion pipeline.

    Steps:
      1. Load .txt files from DOCS_DIR
      2. Chunk each document
      3. Filter out chunks already in ChromaDB (unless overwrite=True)
      4. Embed remaining chunks via Cohere Embed v3
      5. Upsert chunks, embeddings, and metadata into the ChromaDB collection

    Chunk IDs use the format ``<filename>::<chunk_index>`` so that
    re-running ingestion without --overwrite is idempotent.

    Args:
        overwrite: Delete and rebuild the collection if True.
                   Skip already-present chunks if False (default).

    Returns:
        IngestResponse summarising the outcome.

    Raises:
        EnvironmentError: COHERE_API_KEY is not set.
        FileNotFoundError: DOCS_DIR does not exist.
        ValueError: No .txt files found in DOCS_DIR.
    """
    co = _get_cohere_client()
    collection = _get_chroma_collection(overwrite=overwrite)

    docs = _load_documents()
    print(f"\n[ingest] {len(docs)} document(s) found in {DOCS_DIR}")

    # Build the full chunk list with stable IDs and metadata.
    all_chunks: list[dict] = []
    for doc in docs:
        chunks = _chunk_text(doc["text"])
        print(f"[ingest] {doc['name']}: {len(chunks)} chunk(s)")
        for idx, text in enumerate(chunks):
            all_chunks.append(
                {
                    "id": f"{doc['name']}::{idx}",
                    "text": text,
                    "source": doc["name"],
                    "chunk_index": idx,
                }
            )

    if not all_chunks:
        return IngestResponse(
            success=True,
            documents_ingested=0,
            message="No content to ingest — all documents were empty after chunking.",
        )

    # When not overwriting, skip chunks already stored in the collection.
    if not overwrite:
        existing_ids = set(
            collection.get(ids=[c["id"] for c in all_chunks])["ids"]
        )
        new_chunks = [c for c in all_chunks if c["id"] not in existing_ids]

        if not new_chunks:
            return IngestResponse(
                success=True,
                documents_ingested=0,
                message=(
                    f"All {len(all_chunks)} chunk(s) are already present in "
                    f"'{COLLECTION_NAME}'. Use --overwrite to rebuild."
                ),
            )

        if existing_ids:
            print(
                f"[ingest] {len(existing_ids)} chunk(s) already present — "
                f"embedding {len(new_chunks)} new chunk(s)."
            )
        all_chunks = new_chunks

    # Embed and upsert.
    print(f"\n[ingest] Embedding {len(all_chunks)} chunk(s)...")
    embeddings = _embed_chunks(co, [c["text"] for c in all_chunks])

    collection.upsert(
        ids=[c["id"] for c in all_chunks],
        embeddings=embeddings,
        documents=[c["text"] for c in all_chunks],
        metadatas=[
            {"source": c["source"], "chunk_index": c["chunk_index"]}
            for c in all_chunks
        ],
    )

    msg = (
        f"Ingested {len(all_chunks)} chunk(s) from {len(docs)} document(s) "
        f"into collection '{COLLECTION_NAME}'."
    )
    print(f"\n[ingest] Done. {msg}")
    return IngestResponse(success=True, documents_ingested=len(all_chunks), message=msg)


# ---------------------------------------------------------------------------
# CLI entrypoint  (`python -m app.ingest`)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    parser = argparse.ArgumentParser(
        prog="python -m app.ingest",
        description="Ingest knowledge base documents into ChromaDB.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help=(
            "Delete the existing ChromaDB collection and rebuild from scratch. "
            "Default: skip chunks that already exist in the collection."
        ),
    )
    args = parser.parse_args()

    try:
        result = asyncio.run(ingest_documents(overwrite=args.overwrite))
        print(f"\nResult: {result.message}")
        sys.exit(0 if result.success else 1)
    except EnvironmentError as exc:
        print(f"\n[error] Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)
    except (FileNotFoundError, ValueError) as exc:
        print(f"\n[error] {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\n[error] Unexpected error during ingestion: {exc}", file=sys.stderr)
        sys.exit(1)
