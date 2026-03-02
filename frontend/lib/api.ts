/**
 * API layer — all fetch calls live here.
 *
 * No other file should call fetch() directly.
 *
 * BASE resolution:
 *   Development (npm run dev): NEXT_PUBLIC_API_BASE=/api
 *     → calls /api/investigate, handled by app/api/investigate/route.ts
 *     → that route proxies to FastAPI at localhost:8000
 *
 *   Production (npm run build → static export served by FastAPI):
 *     NEXT_PUBLIC_API_BASE is unset (empty string)
 *     → calls /investigate directly on FastAPI (same origin, no proxy needed)
 */

import type {
  AdminResetResponse,
  Case,
  CaseCreate,
  HealthResponse,
  IngestRouteResponse,
  InvestigateRequest,
  InvestigationResult,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

async function _throw(res: Response): Promise<never> {
  const err = await res.json().catch(() => ({ detail: res.statusText }));
  throw new Error((err as { detail?: string }).detail ?? JSON.stringify(err));
}

// ---------------------------------------------------------------------------
// /investigate  (or /api/investigate in dev)
// ---------------------------------------------------------------------------

export async function postInvestigate(
  payload: InvestigateRequest
): Promise<InvestigationResult> {
  const res = await fetch(`${BASE}/investigate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) await _throw(res);
  return res.json() as Promise<InvestigationResult>;
}

// ---------------------------------------------------------------------------
// /health  (or /api/health in dev)
// ---------------------------------------------------------------------------

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json() as Promise<HealthResponse>;
}

// ---------------------------------------------------------------------------
// /ingest  (or /api/ingest in dev)
// ---------------------------------------------------------------------------

export async function postIngest(overwrite = false): Promise<IngestRouteResponse> {
  const url = overwrite ? `${BASE}/ingest?overwrite=true` : `${BASE}/ingest`;
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) throw new Error(`Ingest failed: ${res.statusText}`);
  return res.json() as Promise<IngestRouteResponse>;
}

// ---------------------------------------------------------------------------
// /cases
// ---------------------------------------------------------------------------

export async function postCase(payload: CaseCreate): Promise<Case> {
  const res = await fetch(`${BASE}/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) await _throw(res);
  return res.json() as Promise<Case>;
}

export async function getCases(status?: string): Promise<Case[]> {
  const url = status ? `${BASE}/cases?status=${encodeURIComponent(status)}` : `${BASE}/cases`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch cases: ${res.statusText}`);
  return res.json() as Promise<Case[]>;
}

export async function getCase(id: string): Promise<Case> {
  const res = await fetch(`${BASE}/cases/${encodeURIComponent(id)}`);
  if (!res.ok) await _throw(res);
  return res.json() as Promise<Case>;
}

export async function resolveCase(id: string): Promise<Case> {
  const res = await fetch(`${BASE}/cases/${encodeURIComponent(id)}/resolve`, {
    method: "PATCH",
  });
  if (!res.ok) await _throw(res);
  return res.json() as Promise<Case>;
}

export async function escalateCase(id: string, department: string): Promise<Case> {
  const res = await fetch(`${BASE}/cases/${encodeURIComponent(id)}/escalate`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ department }),
  });
  if (!res.ok) await _throw(res);
  return res.json() as Promise<Case>;
}

// ---------------------------------------------------------------------------
// /admin
// ---------------------------------------------------------------------------

export async function adminReset(): Promise<AdminResetResponse> {
  const res = await fetch(`${BASE}/admin/reset`, { method: "POST" });
  if (!res.ok) await _throw(res);
  return res.json() as Promise<AdminResetResponse>;
}
