"use client";

/**
 * Admin view — database operations and case overview.
 *
 * - Stats row: total / open / investigated / resolved / escalated counts.
 * - "Reset to demo state" button → POST /admin/reset → re-seeds 5 demo cases.
 * - Read-only cases table: id (truncated), client, category, status, created_at.
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import { adminReset, getCases } from "@/lib/api";
import type { Case, CaseStatus } from "@/lib/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_STYLES: Record<CaseStatus, string> = {
  open: "bg-blue-100 text-blue-700 border-blue-200",
  investigated: "bg-amber-100 text-amber-700 border-amber-200",
  resolved: "bg-emerald-100 text-emerald-700 border-emerald-200",
  escalated: "bg-red-100 text-ws-red border-red-200",
};

function fmt(iso: string): string {
  return new Date(iso).toLocaleDateString("en-CA", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AdminPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [resetting, setResetting] = useState(false);
  const [resetMsg, setResetMsg] = useState<string | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);

  async function loadCases() {
    setLoading(true);
    try {
      const data = await getCases();
      setCases(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCases();
  }, []);

  async function handleReset() {
    setResetting(true);
    setResetMsg(null);
    try {
      const r = await adminReset();
      setResetMsg(r.message);
      setConfirmReset(false);
      await loadCases();
    } catch (err) {
      setResetMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setResetting(false);
    }
  }

  // ── Stats ──────────────────────────────────────────────────────────────────

  const stats = {
    total: cases.length,
    open: cases.filter((c) => c.status === "open").length,
    investigated: cases.filter((c) => c.status === "investigated").length,
    resolved: cases.filter((c) => c.status === "resolved").length,
    escalated: cases.filter((c) => c.status === "escalated").length,
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">

      {/* Header */}
      <header className="border-b border-ws-border px-6 py-3 flex items-center gap-2.5 shrink-0">
        <div className="w-5 h-5 bg-dune rounded-full" />
        <span className="text-sm font-bold tracking-tight text-dune">Wealthsimple</span>
        <span className="text-ws-border mx-1.5 select-none">|</span>
        <span className="text-sm font-semibold text-dune">Admin Panel</span>
        <span className="ml-2 text-[10px] font-bold tracking-widest uppercase bg-red-100 text-ws-red border border-red-200 px-2 py-0.5 rounded">
          Admin
        </span>
        <Link href="/" className="ml-auto text-xs text-gray-ws hover:text-dune transition-colors">
          ← Back
        </Link>
      </header>

      <div className="flex-1 max-w-5xl mx-auto w-full px-6 py-10">

        {/* ── Stats row ── */}
        <div className="grid grid-cols-5 gap-4 mb-10">
          {[
            { label: "Total", value: stats.total, color: "text-dune" },
            { label: "Open", value: stats.open, color: "text-blue-700" },
            { label: "Investigated", value: stats.investigated, color: "text-amber-700" },
            { label: "Resolved", value: stats.resolved, color: "text-emerald-700" },
            { label: "Escalated", value: stats.escalated, color: "text-ws-red" },
          ].map(({ label, value, color }) => (
            <div
              key={label}
              className="border border-ws-border rounded-lg px-4 py-4 bg-light text-center"
            >
              <p className={`text-2xl font-bold tracking-tight ${color}`}>{value}</p>
              <p className="text-[11px] text-gray-ws uppercase tracking-wider mt-1">{label}</p>
            </div>
          ))}
        </div>

        {/* ── Reset section ── */}
        <div className="border border-ws-border rounded-lg px-6 py-5 mb-8">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-sm font-bold text-dune mb-1">Reset to demo state</h2>
              <p className="text-xs text-gray-ws">
                Deletes all cases and re-seeds 5 representative demo cases. This is
                irreversible — all investigation results and actions will be lost.
              </p>
            </div>

            {!confirmReset ? (
              <button
                onClick={() => setConfirmReset(true)}
                className="shrink-0 border border-ws-red text-ws-red text-[11px] font-bold tracking-widest uppercase px-4 py-2 rounded hover:bg-red-50 transition-colors"
              >
                Reset Database
              </button>
            ) : (
              <div className="shrink-0 flex items-center gap-2">
                <button
                  onClick={handleReset}
                  disabled={resetting}
                  className="bg-ws-red text-white text-[11px] font-bold tracking-widest uppercase px-4 py-2 rounded hover:bg-opacity-90 transition-opacity disabled:opacity-50"
                >
                  {resetting ? "Resetting…" : "Confirm Reset"}
                </button>
                <button
                  onClick={() => setConfirmReset(false)}
                  className="text-xs font-semibold text-gray-ws underline underline-offset-2"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>

          {resetMsg && (
            <p className="mt-3 text-xs text-emerald-700 font-semibold">{resetMsg}</p>
          )}
        </div>

        {/* ── Cases table ── */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-[11px] font-bold text-dune uppercase tracking-wider">
              All Cases
            </h2>
            <button
              onClick={loadCases}
              disabled={loading}
              className="text-xs font-semibold text-gray-ws underline underline-offset-2 disabled:opacity-50"
            >
              {loading ? "Refreshing…" : "Refresh"}
            </button>
          </div>

          {error && (
            <p className="text-xs text-ws-red mb-4">{error}</p>
          )}

          <div className="border border-ws-border rounded-lg overflow-hidden">
            {/* Table header */}
            <div className="grid grid-cols-[1fr_1fr_1.5fr_1fr_1fr] bg-light border-b border-ws-border px-4 py-2.5">
              {["Complaint #", "Client", "Category", "Status", "Created"].map((h) => (
                <span key={h} className="text-[10px] font-bold text-dune uppercase tracking-wider">
                  {h}
                </span>
              ))}
            </div>

            {/* Rows */}
            {loading && cases.length === 0 ? (
              <div className="px-4 py-6 text-center text-xs text-gray-ws">Loading…</div>
            ) : cases.length === 0 ? (
              <div className="px-4 py-6 text-center text-xs text-gray-ws">No cases found.</div>
            ) : (
              cases.map((c) => (
                <div
                  key={c.id}
                  className="grid grid-cols-[1fr_1fr_1.5fr_1fr_1fr] px-4 py-3 border-b border-ws-border last:border-b-0 hover:bg-[#FAFAF8] transition-colors"
                >
                  <span className="text-[11px] font-mono text-gray-ws">#{c.id.slice(0, 8)}</span>
                  <span className="text-[11px] text-dune">{c.client_id}</span>
                  <span className="text-[11px] text-dune">{c.category}</span>
                  <span>
                    <span className={`text-[10px] font-semibold border px-1.5 py-0.5 rounded ${STATUS_STYLES[c.status]}`}>
                      {c.status}
                    </span>
                  </span>
                  <span className="text-[11px] text-gray-ws">{fmt(c.created_at)}</span>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
