/**
 * TypeScript interfaces mirroring app/models.py.
 *
 * Single source of truth for all data shapes shared between the frontend
 * and the FastAPI backend. When app/models.py changes, update this file.
 *
 * No imports — types only.
 */

// ---------------------------------------------------------------------------
// /investigate
// ---------------------------------------------------------------------------

export interface InvestigateRequest {
  complaint: string;
  /** If provided, saves the result to this case and sets status='investigated'. */
  case_id?: string;
}

/** The four failure-point literals from InvestigationResult.failure_point. */
export type FailurePoint = "wealthsimple" | "institution" | "client" | "unknown";

/** The three recommended-action literals from InvestigationResult.recommended_action. */
export type RecommendedAction = "send_response" | "escalate" | "investigate_further";

/** Mirrors InvestigationResult in app/models.py */
export interface InvestigationResult {
  timeline_reconstruction: string;
  failure_point: FailurePoint;
  draft_client_response: string;
  confidence_score: number; // 0.0–1.0
  sources: string[];
  escalation_flags: string[];
  recommended_action: RecommendedAction;
  relevant_departments: string[];
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

// ---------------------------------------------------------------------------
// /cases
// ---------------------------------------------------------------------------

export type CaseStatus = "open" | "investigated" | "resolved" | "escalated";

export type TriageCategory =
  | "Institutional Delay"
  | "Wire Transfer Issue"
  | "Missing Funds"
  | "Account Restriction"
  | "Transfer Rejected";

/** Mirrors CaseCreate in app/models.py */
export interface CaseCreate {
  client_id: string;
  category: TriageCategory;
  complaint: string;
}

/** Mirrors CaseResponse in app/models.py */
export interface Case {
  id: string;
  client_id: string;
  category: TriageCategory;
  complaint: string;
  status: CaseStatus;
  result_json: InvestigationResult | null;
  action_taken: "replied" | "escalated" | null;
  department: string | null;
  created_at: string; // ISO 8601
  resolved_at: string | null;
}

// ---------------------------------------------------------------------------
// /admin
// ---------------------------------------------------------------------------

/** Mirrors AdminResetResponse in app/models.py */
export interface AdminResetResponse {
  seeded: number;
  message: string;
}

// ---------------------------------------------------------------------------
// QueuedComplaint (UI only — kept for WorkflowStepper + badge colour map)
// ---------------------------------------------------------------------------

export interface QueuedComplaint {
  id: string;
  clientId: string;
  category: TriageCategory;
  text: string;
}
