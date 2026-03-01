/**
 * API layer — all fetch calls live here.
 *
 * No other file should call fetch() directly. This makes the API contract
 * explicit and the surface easy to swap when migrating to React (e.g. with
 * React Query wrapping these same functions).
 *
 * BASE is an empty string so all URLs are relative. During development Vite's
 * proxy forwards them to FastAPI on port 8000. In production, FastAPI serves
 * the built frontend from the same origin, so no proxy is needed.
 */

import type {
  HealthResponse,
  IngestRouteResponse,
  InvestigateRequest,
  InvestigationResult,
} from "./types";

const BASE = "";

// ---------------------------------------------------------------------------
// /investigate
// ---------------------------------------------------------------------------

export async function postInvestigate(
  payload: InvestigateRequest
): Promise<InvestigationResult> {
  const res = await fetch(`${BASE}/investigate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail ?? JSON.stringify(err));
  }

  return res.json() as Promise<InvestigationResult>;
}

// ---------------------------------------------------------------------------
// /health
// ---------------------------------------------------------------------------

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json() as Promise<HealthResponse>;
}

// ---------------------------------------------------------------------------
// /ingest
// ---------------------------------------------------------------------------

export async function postIngest(overwrite = false): Promise<IngestRouteResponse> {
  const url = overwrite ? `${BASE}/ingest?overwrite=true` : `${BASE}/ingest`;
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) throw new Error(`Ingest failed: ${res.statusText}`);
  return res.json() as Promise<IngestRouteResponse>;
}
