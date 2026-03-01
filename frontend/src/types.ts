/**
 * TypeScript interfaces mirroring app/models.py.
 *
 * This file is the single source of truth for all data shapes shared between
 * the frontend and the FastAPI backend. When app/models.py changes, update
 * this file to match.
 *
 * No imports — types only. Framework-agnostic: used unchanged after migration
 * to React/Next.js.
 */

// ---------------------------------------------------------------------------
// /investigate
// ---------------------------------------------------------------------------

export interface InvestigateRequest {
  complaint: string;
}

/** The four failure-point literals from InvestigationResult.failure_point. */
export type FailurePoint = "wealthsimple" | "institution" | "client" | "unknown";

/** Mirrors InvestigationResult in app/models.py */
export interface InvestigationResult {
  timeline_reconstruction: string;
  failure_point: FailurePoint;
  draft_client_response: string;
  confidence_score: number; // 0.0–1.0
  sources: string[];
  escalation_flags: string[];
}

// ---------------------------------------------------------------------------
// /ingest
// ---------------------------------------------------------------------------

/** Mirrors IngestRouteResponse in app/models.py */
export interface IngestRouteResponse {
  status: string;
  chunks_indexed: number;
  message: string;
}

// ---------------------------------------------------------------------------
// /health
// ---------------------------------------------------------------------------

/** Mirrors HealthResponse in app/models.py */
export interface HealthResponse {
  status: string;
  knowledge_base_size: number;
}
