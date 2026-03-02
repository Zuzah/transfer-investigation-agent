"""
Query / investigation pipeline for the Transfer Investigation Agent.

Pipeline steps:
  1. Embed the complaint using Cohere Embed v3 (search_query input type)
  2. Retrieve the top 20 candidate chunks from ChromaDB
  3. Rerank candidates to the top 5 using Cohere Rerank v3
  4. Build a grounded prompt for Command R+ (command-r-plus-08-2024)
  5. Call Command R+ and parse its JSON output into InvestigationResult

The returned InvestigationResult is a draft for human review.
It must not be sent to clients without operator approval.
"""

import json
import logging
import os
import re
from pathlib import Path

import chromadb
import cohere
from dotenv import load_dotenv

from app.models import InvestigateRequest, InvestigationResult

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — must match the values used in app/ingest.py
# ---------------------------------------------------------------------------

CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME = "transfer_knowledge"

CANDIDATE_COUNT = 20   # chunks fetched from ChromaDB before reranking
RERANK_TOP_N = 5       # chunks kept after Cohere Rerank

# Cohere Rerank v3 relevance_score values for relevant RAG documents in this
# domain (short complaint queries vs. long procedural docs) empirically fall
# in the 0.05–0.20 range. Dividing the weighted average by this ceiling maps
# a "good" match (~0.16) to ~80% confidence instead of ~30%.
RERANK_SCORE_CEILING = 0.20

VALID_FAILURE_POINTS = {"wealthsimple", "institution", "client", "unknown"}


# ---------------------------------------------------------------------------
# Client initialisation
# ---------------------------------------------------------------------------

def _build_cohere_client() -> cohere.Client:
    """
    Return a Cohere client authenticated with COHERE_API_KEY.

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


def _build_chroma_collection() -> chromadb.Collection:
    """
    Return the persisted ChromaDB collection used for retrieval.

    Raises:
        RuntimeError: If the collection does not exist (ingestion has not been run).
    """
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        return client.get_collection(name=COLLECTION_NAME)
    except Exception:
        raise RuntimeError(
            f"ChromaDB collection '{COLLECTION_NAME}' not found. "
            "Run `python -m app.ingest` to build the knowledge base first."
        )


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def _embed_query(co: cohere.Client, complaint: str) -> list[float]:
    """
    Embed the complaint text using Cohere Embed v3.

    Uses input_type="search_query" so the embedding is optimised for
    retrieval against documents embedded with input_type="search_document".

    Args:
        co: Authenticated Cohere client.
        complaint: The free-text transfer complaint.

    Returns:
        Embedding vector as a list of floats.
    """
    response = co.embed(
        texts=[complaint],
        model="embed-english-v3.0",
        input_type="search_query",
    )
    return response.embeddings[0]


def _retrieve_candidates(
    collection: chromadb.Collection,
    embedding: list[float],
    n: int = CANDIDATE_COUNT,
) -> list[dict]:
    """
    Query ChromaDB for the top `n` most similar chunks to the complaint embedding.

    Args:
        collection: The ChromaDB collection to query.
        embedding: Query embedding vector.
        n: Number of candidates to return (default: CANDIDATE_COUNT).

    Returns:
        List of dicts, each with keys:
          - 'text'   (str): The chunk text.
          - 'source' (str): Source document filename.
          - 'score'  (float): Cosine similarity score (lower distance = higher similarity).
    """
    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(n, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    candidates = []
    for text, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        candidates.append(
            {
                "text": text,
                "source": meta.get("source", "unknown"),
                "score": 1.0 - dist,  # convert cosine distance to similarity
            }
        )
    return candidates


def _rerank(
    co: cohere.Client,
    complaint: str,
    candidates: list[dict],
    top_n: int = RERANK_TOP_N,
) -> list[dict]:
    """
    Rerank candidate chunks using Cohere Rerank v3 and return the top `top_n`.

    Reranking improves retrieval precision by applying a cross-encoder that
    reads the complaint and each candidate chunk together, producing a more
    accurate relevance score than the initial embedding similarity.

    Args:
        co: Authenticated Cohere client.
        complaint: The original complaint text (used as the rerank query).
        candidates: Candidate chunks from ChromaDB retrieval.
        top_n: Number of chunks to keep after reranking (default: RERANK_TOP_N).

    Returns:
        Top `top_n` chunks from `candidates`, ordered by rerank relevance score
        (descending), each dict augmented with a 'rerank_score' key.
    """
    response = co.rerank(
        model="rerank-english-v3.0",
        query=complaint,
        documents=[c["text"] for c in candidates],
        top_n=top_n,
    )

    reranked = []
    for result in response.results:
        chunk = dict(candidates[result.index])
        chunk["rerank_score"] = result.relevance_score
        reranked.append(chunk)

    return reranked


def _build_messages(complaint: str, chunks: list[dict]) -> tuple[str, str]:
    """
    Build the system prompt and user message for Command R+.

    The system prompt establishes the analyst role and hard rules
    (cite sources, flag what needs human verification, no jargon in drafts).
    The user message provides the retrieved context and the complaint,
    then asks for a strict JSON response.

    Args:
        complaint: The original complaint text.
        chunks: Reranked knowledge base chunks with 'text' and 'source' keys.

    Returns:
        Tuple of (system_prompt, user_message).
    """
    system_prompt = """\
You are a senior payment operations analyst at Wealthsimple. \
Your role is to investigate transfer complaints using internal process documentation \
and produce structured analysis for human agents to review before contacting clients.

RULES YOU MUST FOLLOW:
1. Cite the source document filename for every factual claim about process or timelines.
2. Be specific about which step in the transfer process likely failed — \
do not give a vague answer like "something went wrong at the institution".
3. The draft_client_response must be written in plain language. \
No internal jargon, no system names, no process step numbers. \
Write as if speaking directly to the client, but remember this is a DRAFT for a human agent to review.
4. End the draft_client_response with a line explicitly stating what the \
human agent must verify or confirm before approving and sending the response.
5. Assign a confidence_score between 0.0 and 1.0. \
Lower confidence if: the complaint lacks dates or amounts, the failure point is ambiguous, \
or multiple explanations are equally plausible.
6. Populate escalation_flags with any of the following if applicable: \
"potential_fraud", "regulatory_reporting_required", "supervisor_approval_required", \
"large_transaction_review", "account_restriction_possible", or any other specific flag \
warranted by the complaint. Use an empty array if none apply.
7. Financial remedy decisions (refunds, fee waivers, compensation) are NOT your role. \
Never suggest or promise a remedy in the draft. A human will make that decision.
"""

    context_blocks = []
    for i, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[DOC {i} — {chunk['source']}]\n{chunk['text']}"
        )
    context_section = "\n\n".join(context_blocks)

    # Truncate complaint to 2000 chars max for the prompt — log if truncated.
    complaint_display = complaint[:2000]
    if len(complaint) > 2000:
        complaint_display += "\n[... truncated for length]"
        logger.warning(
            "Complaint truncated in prompt: original %d chars", len(complaint)
        )

    user_message = f"""\
## PROCESS DOCUMENTATION (Retrieved from knowledge base)

{context_section}

---

## COMPLAINT

{complaint_display}

---

## TASK

Analyse the complaint above using only the process documentation provided. \
Return a single JSON object with exactly the following fields and no other text:

{{
  "timeline_reconstruction": "<Step-by-step reconstruction of what likely happened. \
Compare expected process timelines from the documentation against the dates and \
durations mentioned in the complaint. Identify where the process diverged.>",

  "failure_point": "<Exactly one of: wealthsimple | institution | client | unknown>",

  "draft_client_response": "<Plain-language explanation for the client covering: \
(1) what we believe happened, (2) what is being done, (3) expected next steps. \
End the draft with a line beginning 'AGENT MUST VERIFY:' listing what the human \
agent should confirm before sending this response.>",

  "confidence_score": <float between 0.0 and 1.0>,

  "escalation_flags": [<list of flag strings, or empty array>]
}}

Return only valid JSON. Do not include markdown fences, commentary, or any text \
outside the JSON object.
"""

    return system_prompt, user_message


def _compute_confidence(chunks: list[dict]) -> float:
    """
    Compute a stable, reproducible confidence score from rerank scores.

    Uses a weighted average: the top chunk contributes 50% and the mean of the
    remaining chunks contributes 50%. This rewards both a strong best match and
    broad supporting evidence.

    The weighted average is then normalised against RERANK_SCORE_CEILING (0.20)
    because Cohere Rerank v3 relevance_score values for relevant RAG documents
    in this domain (short complaint queries vs. long procedural docs) empirically
    fall in the 0.05–0.20 range. Without normalisation a well-matched complaint
    scores ~28% even when retrieval quality is high. After normalisation a top
    score of ~0.16 maps to ~80% confidence.

    Rerank scores are deterministic for the same input, so this value is
    consistent across repeated calls — unlike the model's self-reported score
    which varies with temperature.

    Args:
        chunks: Reranked chunks, each expected to have a 'rerank_score' key.

    Returns:
        Float in [0.0, 1.0], rounded to 2 decimal places.
    """
    if not chunks:
        return 0.0
    scores = [c.get("rerank_score", 0.0) for c in chunks]
    top = scores[0]
    rest_avg = sum(scores[1:]) / len(scores[1:]) if len(scores) > 1 else top
    raw = top * 0.5 + rest_avg * 0.5
    return round(min(1.0, max(0.0, raw / RERANK_SCORE_CEILING)), 2)


def _parse_model_output(raw: str, chunks: list[dict]) -> InvestigationResult:
    """
    Parse Command R+'s raw text output into an InvestigationResult.

    Attempts JSON extraction in order:
      1. Direct json.loads on the stripped response
      2. Extraction from a markdown JSON code fence (```json ... ```)
      3. Extraction of the outermost {...} block via regex

    If all parsing attempts fail, returns a safe fallback result with
    failure_point="unknown", a low confidence score, and an escalation flag
    so the human agent knows the analysis could not be structured.

    Args:
        raw: Raw string response from Command R+.
        chunks: Reranked chunks used for this query (to derive the sources list).

    Returns:
        Populated InvestigationResult.
    """
    sources = sorted({c["source"] for c in chunks})

    # --- Attempt 1: direct parse ---
    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError:
        # --- Attempt 2: extract from ```json ... ``` fence ---
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
        if fence_match:
            try:
                data = json.loads(fence_match.group(1))
            except json.JSONDecodeError:
                data = None
        else:
            data = None

    if data is None:
        # --- Attempt 3: find outermost {...} block ---
        brace_match = re.search(r"\{[\s\S]*\}", raw)
        if brace_match:
            try:
                data = json.loads(brace_match.group())
            except json.JSONDecodeError:
                data = None

    if data is None:
        logger.error(
            "Failed to parse model output as JSON. Raw response (first 200 chars): %s",
            raw[:200],
        )
        return InvestigationResult(
            timeline_reconstruction="[Model output could not be parsed. Manual review required.]",
            failure_point="unknown",
            draft_client_response=(
                "[Draft could not be generated — model output was not valid JSON. "
                "A human agent must investigate this complaint manually.]\n\n"
                "AGENT MUST VERIFY: Everything. This result requires full manual review."
            ),
            confidence_score=0.0,
            sources=sources,
            escalation_flags=["model_output_parse_failure", "manual_review_required"],
        )

    # --- Validate and normalise failure_point ---
    raw_fp = str(data.get("failure_point", "unknown")).strip().lower()
    failure_point = raw_fp if raw_fp in VALID_FAILURE_POINTS else "unknown"

    # --- Clamp confidence_score to [0.0, 1.0] ---
    try:
        confidence = float(data.get("confidence_score", 0.5))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.5

    # --- Normalise escalation_flags ---
    raw_flags = data.get("escalation_flags", [])
    if isinstance(raw_flags, list):
        escalation_flags = [str(f) for f in raw_flags if f]
    else:
        escalation_flags = [str(raw_flags)] if raw_flags else []

    return InvestigationResult(
        timeline_reconstruction=str(data.get("timeline_reconstruction", "")).strip(),
        failure_point=failure_point,
        draft_client_response=str(data.get("draft_client_response", "")).strip(),
        confidence_score=confidence,
        sources=sources,
        escalation_flags=escalation_flags,
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def investigate(complaint: str) -> InvestigationResult:
    """
    Run the full investigation pipeline for a transfer complaint.

    Steps:
      1. Embed the complaint with Cohere Embed v3 (search_query)
      2. Retrieve the top CANDIDATE_COUNT chunks from ChromaDB
      3. Rerank to the top RERANK_TOP_N chunks with Cohere Rerank v3
      4. Build a grounded prompt for Command R+ (command-r-plus-08-2024)
      5. Call Command R+ and parse the JSON output

    Args:
        complaint: Free-text description of the transfer complaint.

    Returns:
        InvestigationResult with timeline, failure point, draft response,
        confidence score, sources, and escalation flags.

    Raises:
        EnvironmentError: COHERE_API_KEY is not set.
        RuntimeError: The ChromaDB collection does not exist (run ingest first).
    """
    # Log a truncated version of the complaint — never log the full text.
    logger.info(
        "Investigation started. Complaint preview: %.100s...",
        complaint,
    )

    co = _build_cohere_client()
    collection = _build_chroma_collection()

    embedding = _embed_query(co, complaint)
    candidates = _retrieve_candidates(collection, embedding)
    top_chunks = _rerank(co, complaint, candidates)

    rerank_scores = [round(c["rerank_score"], 4) for c in top_chunks]
    logger.info(
        "Retrieved %d candidates, reranked to %d chunks. Sources: %s",
        len(candidates),
        len(top_chunks),
        [c["source"] for c in top_chunks],
    )
    print(
        f"[query] Rerank scores: {rerank_scores} | "
        f"Computed confidence: {_compute_confidence(top_chunks):.2f}"
    )

    system_prompt, user_message = _build_messages(complaint, top_chunks)

    response = co.chat(
        model="command-r-plus-08-2024",
        message=user_message,
        preamble=system_prompt,
        temperature=0.0,  # deterministic output — same complaint → same draft
    )

    result = _parse_model_output(response.text, top_chunks)

    # Override the model's self-reported confidence with a value derived from
    # rerank scores, which are deterministic and grounded in evidence quality.
    result = result.model_copy(
        update={"confidence_score": _compute_confidence(top_chunks)}
    )

    logger.info(
        "Investigation complete. failure_point=%s confidence=%.2f flags=%s",
        result.failure_point,
        result.confidence_score,
        result.escalation_flags,
    )

    return result


async def run_investigation(request: InvestigateRequest) -> InvestigationResult:
    """
    Route adapter for POST /investigate.

    Extracts the complaint string from the request and delegates to investigate().

    Args:
        request: Validated InvestigateRequest from the FastAPI route.

    Returns:
        InvestigationResult from the investigation pipeline.
    """
    return await investigate(request.complaint)


def knowledge_base_size() -> int:
    """
    Return the number of chunks currently stored in the ChromaDB collection.

    Used by GET /health to report knowledge base readiness.
    Returns 0 if the collection has not yet been created (ingest not yet run)
    rather than raising, so the health endpoint always responds.

    Returns:
        Integer count of stored chunks, or 0 if the collection is absent.
    """
    try:
        collection = _build_chroma_collection()
        return collection.count()
    except RuntimeError:
        return 0
