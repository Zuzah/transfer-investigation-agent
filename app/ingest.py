"""
Document ingestion pipeline for the Transfer Investigation Agent.

Responsibilities:
  1. Read all .txt files from knowledge_base/docs/
  2. Chunk documents into manageable segments
  3. Generate embeddings using Cohere's embedding API
  4. Upsert chunks + embeddings into ChromaDB

Configuration is read from environment variables (see .env.example).
"""

import os
from pathlib import Path
from app.models import IngestResponse

# TODO: import chromadb
# TODO: import cohere

DOCS_DIR = Path(__file__).parent.parent / "knowledge_base" / "docs"

# TODO: Configure ChromaDB client
# chroma_client = chromadb.Client()
# collection = chroma_client.get_or_create_collection("transfer_docs")

# TODO: Configure Cohere client
# co = cohere.Client(os.getenv("COHERE_API_KEY"))


def _load_documents() -> list[dict]:
    """
    Load all .txt files from DOCS_DIR.

    Returns a list of dicts with keys:
      - 'name': filename (str)
      - 'text': full file content (str)

    TODO: implement file loading
    """
    # TODO: iterate DOCS_DIR.glob("*.txt"), read each file, return list of dicts
    raise NotImplementedError("_load_documents not yet implemented")


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping chunks of approximately chunk_size characters.

    Args:
        text: The full document text.
        chunk_size: Target size of each chunk in characters.
        overlap: Number of characters to overlap between consecutive chunks.

    Returns:
        List of text chunks.

    TODO: implement chunking strategy (character-based or sentence-aware)
    """
    # TODO: implement chunking; consider using a sentence splitter for cleaner boundaries
    raise NotImplementedError("_chunk_text not yet implemented")


async def ingest_documents() -> IngestResponse:
    """
    Orchestrate the full ingestion pipeline.

    Steps:
      1. Load documents from DOCS_DIR via _load_documents()
      2. Chunk each document via _chunk_text()
      3. Embed all chunks using Cohere embed API
      4. Upsert into ChromaDB collection with metadata (source filename, chunk index)

    Returns:
        IngestResponse with the count of ingested chunks.

    TODO: implement this function
    """
    # TODO: implement ingestion pipeline
    # Example skeleton:
    #   docs = _load_documents()
    #   all_chunks = []
    #   for doc in docs:
    #       chunks = _chunk_text(doc["text"])
    #       all_chunks.extend({"text": c, "source": doc["name"], "idx": i} for i, c in enumerate(chunks))
    #   embeddings = co.embed(texts=[c["text"] for c in all_chunks], model="embed-english-v3.0", input_type="search_document").embeddings
    #   collection.upsert(ids=[...], embeddings=embeddings, documents=[...], metadatas=[...])
    raise NotImplementedError("ingest_documents not yet implemented")
