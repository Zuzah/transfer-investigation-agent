"use client";

/**
 * Analyst view — two-panel investigation workspace.
 *
 * Left panel:  ComplaintQueue — live case list, polls GET /cases every 15 s.
 * Right panel: WorkflowStepper + ComplaintInput + ResultsPanel.
 *
 * Workflow:
 *  1. Select a case from the queue → complaint pre-filled, step = 1.
 *  2. Click Investigate → POST /investigate (with case_id) → step = 4 (Agent Review).
 *  3a. Approve & Send → PATCH /cases/{id}/resolve → step = 5.
 *  3b. Escalate → department picker → PATCH /cases/{id}/escalate → step = 5.
 *
 * Cases that already have result_json load immediately at step 4.
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  getCases,
  escalateCase,
  postInvestigate,
  resolveCase,
} from "@/lib/api";
import type { Case, InvestigationResult } from "@/lib/types";
import ComplaintQueue from "@/components/ComplaintQueue";
import ComplaintInput from "@/components/ComplaintInput";
import ResultsPanel from "@/components/ResultsPanel";
import WorkflowStepper from "@/components/WorkflowStepper";

// ---------------------------------------------------------------------------
// Department list — mirrors VALID_DEPARTMENTS in app/query.py
// ---------------------------------------------------------------------------

const ALL_DEPARTMENTS = [
  "Payment Operations",
  "Compliance & AML",
  "Client Relations",
  "Banking Operations",
  "Risk Management",
  "Regulatory Reporting",
];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AnalystPage() {
  // ── Case queue ────────────────────────────────────────────────────────────
  const [cases, setCases] = useState<Case[]>([]);
  const [queueLoading, setQueueLoading] = useState(true);
  const [queueError, setQueueError] = useState<string | null>(null);

  // ── Active case + workspace ───────────────────────────────────────────────
  const [activeCase, setActiveCase] = useState<Case | null>(null);
  const [complaint, setComplaint] = useState("");
  const [step, setStep] = useState(1);
  const [reviewedIds, setReviewedIds] = useState<Set<string>>(new Set());

  // ── Investigation ─────────────────────────────────────────────────────────
  const [investigating, setInvestigating] = useState(false);
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [investigateError, setInvestigateError] = useState<string | null>(null);

  // ── Approve / Escalate ────────────────────────────────────────────────────
  const [resolving, setResolving] = useState(false);
  const [showEscalate, setShowEscalate] = useState(false);
  const [escalateDept, setEscalateDept] = useState("");
  const [escalating, setEscalating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // ── Load + poll cases ─────────────────────────────────────────────────────

  async function loadCases() {
    try {
      const data = await getCases();
      setCases(data);
      setQueueError(null);
    } catch (err) {
      setQueueError(err instanceof Error ? err.message : String(err));
    } finally {
      setQueueLoading(false);
    }
  }

  useEffect(() => {
    loadCases();
    const interval = setInterval(loadCases, 15_000);
    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Select a case from the queue ──────────────────────────────────────────

  function handleSelectCase(c: Case) {
    setActiveCase(c);
    setComplaint(c.complaint);
    setInvestigateError(null);
    setActionError(null);
    setShowEscalate(false);
    setEscalateDept("");

    setReviewedIds((prev) => { const next = new Set(prev); next.add(c.id); return next; });

    // If the case already has a result from a previous investigation, load it
    if (c.result_json) {
      setResult(c.result_json);
      setStep(c.status === "open" ? 4 : 5);
    } else {
      setResult(null);
      setStep(1);
    }
  }

  // ── Investigate ───────────────────────────────────────────────────────────

  async function handleInvestigate() {
    if (!complaint.trim() || investigating) return;
    setInvestigating(true);
    setInvestigateError(null);
    setStep(2);

    try {
      const r = await postInvestigate({
        complaint: complaint.trim(),
        case_id: activeCase?.id,
      });
      setResult(r);
      setStep(4);

      // Update the case in the local list so the queue dot changes immediately
      if (activeCase) {
        const updated: Case = {
          ...activeCase,
          status: "investigated",
          result_json: r,
        };
        setActiveCase(updated);
        setCases((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      }
    } catch (err) {
      setInvestigateError(err instanceof Error ? err.message : String(err));
      setStep(1);
    } finally {
      setInvestigating(false);
    }
  }

  // ── Approve & Send ────────────────────────────────────────────────────────

  async function handleApprove() {
    if (!activeCase || resolving) return;
    setResolving(true);
    setActionError(null);
    try {
      const updated = await resolveCase(activeCase.id);
      setActiveCase(updated);
      setCases((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      setStep(5);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    } finally {
      setResolving(false);
    }
  }

  // ── Escalate ──────────────────────────────────────────────────────────────

  async function handleEscalate() {
    if (!activeCase || escalating || !escalateDept) return;
    setEscalating(true);
    setActionError(null);
    try {
      const updated = await escalateCase(activeCase.id, escalateDept);
      setActiveCase(updated);
      setCases((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      setStep(5);
      setShowEscalate(false);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    } finally {
      setEscalating(false);
    }
  }

  // ── Department list for escalation picker ─────────────────────────────────

  const deptOptions =
    result?.relevant_departments && result.relevant_departments.length > 0
      ? result.relevant_departments
      : ALL_DEPARTMENTS;

  // ── Render ────────────────────────────────────────────────────────────────

  const isActioned = activeCase?.status === "resolved" || activeCase?.status === "escalated";

  return (
    <div className="min-h-screen bg-white flex flex-col">

      {/* Header */}
      <header className="border-b border-ws-border px-6 py-3 flex items-center gap-2.5 shrink-0">
        <div className="w-5 h-5 bg-dune rounded-full" />
        <span className="text-sm font-bold tracking-tight text-dune">Wealthsimple</span>
        <span className="text-ws-border mx-1.5 select-none">|</span>
        <span className="text-sm font-semibold text-dune">Transfer Investigation</span>
        <span className="ml-2 text-[10px] font-bold tracking-widest uppercase bg-amber-100 text-amber-700 border border-amber-200 px-2 py-0.5 rounded">
          Analyst
        </span>
        <Link href="/" className="ml-auto text-xs text-gray-ws hover:text-dune transition-colors">
          ← Back
        </Link>
      </header>

      {/* Two-panel workspace */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── Left: Complaint Queue ── */}
        {queueLoading && cases.length === 0 ? (
          <aside className="w-[30%] min-w-[260px] border-r border-ws-border flex items-center justify-center shrink-0">
            <p className="text-xs text-gray-ws">Loading cases…</p>
          </aside>
        ) : queueError ? (
          <aside className="w-[30%] min-w-[260px] border-r border-ws-border flex items-center justify-center shrink-0 px-4">
            <p className="text-xs text-ws-red text-center">{queueError}</p>
          </aside>
        ) : (
          <ComplaintQueue
            cases={cases}
            activeId={activeCase?.id ?? null}
            reviewedIds={reviewedIds}
            onSelect={handleSelectCase}
          />
        )}

        {/* ── Right: Workspace ── */}
        <main className="flex-1 overflow-y-auto px-8 py-8">
          <WorkflowStepper step={step} />

          {/* Resolved / escalated banner */}
          {step === 5 && activeCase && (
            <div className={`mb-6 border rounded-lg px-5 py-4 flex items-center gap-3
              ${activeCase.status === "resolved"
                ? "bg-emerald-50 border-emerald-200"
                : "bg-red-50 border-red-200"}`}
            >
              <div className={`w-2 h-2 rounded-full shrink-0
                ${activeCase.status === "resolved" ? "bg-emerald-500" : "bg-ws-red"}`}
              />
              <div>
                <p className={`text-sm font-semibold
                  ${activeCase.status === "resolved" ? "text-emerald-800" : "text-ws-red"}`}>
                  {activeCase.status === "resolved"
                    ? "Response sent to client"
                    : `Escalated to ${activeCase.department}`}
                </p>
                <p className="text-xs text-gray-ws mt-0.5">
                  Case {activeCase.id.slice(0, 8)} · {activeCase.status}
                </p>
              </div>
            </div>
          )}

          <ComplaintInput
            value={complaint}
            onChange={setComplaint}
            onInvestigate={handleInvestigate}
            loading={investigating}
          />

          {investigateError && (
            <div className="bg-[#FDF2F2] border border-[#E8C4C4] border-l-[3px] border-l-ws-red rounded px-4 py-3 text-ws-red text-sm mb-6">
              {investigateError}
            </div>
          )}

          {result && (
            <>
              <ResultsPanel
                result={result}
                onApprove={handleApprove}
              />

              {/* ── Action footer ── */}
              {!isActioned && (
                <div className="mt-4">
                  {actionError && (
                    <p className="text-xs text-ws-red mb-3">{actionError}</p>
                  )}

                  {!showEscalate ? (
                    <div className="flex items-center gap-3">
                      <button
                        onClick={handleApprove}
                        disabled={resolving || escalating}
                        className="bg-gold text-dune text-[11px] font-bold tracking-widest uppercase px-5 py-2.5 rounded hover:bg-opacity-80 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {resolving ? "Sending…" : "Approve & Send"}
                      </button>
                      <button
                        onClick={() => {
                          setShowEscalate(true);
                          setEscalateDept(deptOptions[0] ?? "");
                        }}
                        disabled={resolving || escalating}
                        className="border border-ws-border text-dune text-[11px] font-bold tracking-widest uppercase px-5 py-2.5 rounded hover:bg-light transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        Escalate
                      </button>
                    </div>
                  ) : (
                    <div className="border border-ws-border rounded-lg px-5 py-4 bg-light">
                      <h4 className="text-[11px] font-bold text-dune uppercase tracking-wider mb-3">
                        Escalate to department
                      </h4>
                      <select
                        value={escalateDept}
                        onChange={(e) => setEscalateDept(e.target.value)}
                        className="w-full border border-ws-border rounded px-4 py-2.5 text-sm text-dune bg-white focus:outline-none focus:ring-2 focus:ring-gold focus:border-gold mb-3"
                      >
                        {deptOptions.map((d) => (
                          <option key={d} value={d}>{d}</option>
                        ))}
                      </select>
                      <div className="flex items-center gap-3">
                        <button
                          onClick={handleEscalate}
                          disabled={escalating || !escalateDept}
                          className="bg-dune text-white text-[11px] font-bold tracking-widest uppercase px-5 py-2.5 rounded hover:bg-opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          {escalating ? "Escalating…" : "Confirm Escalation"}
                        </button>
                        <button
                          onClick={() => setShowEscalate(false)}
                          className="text-xs font-semibold text-gray-ws underline underline-offset-2"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {!activeCase && !result && (
            <div className="mt-8 border border-dashed border-ws-border rounded-lg px-6 py-10 text-center">
              <p className="text-sm text-gray-ws">
                Select a complaint from the queue to begin investigation.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
