"use client";

/**
 * Investigation page — two-panel ops workflow tool.
 *
 * Left panel  (30%): Complaint Queue — 5 pre-loaded complaint cards.
 *                    Clicking a card pre-fills the workspace and marks it active.
 *
 * Right panel (70%): Investigation Workspace
 *                    - Workflow stepper (5 steps)
 *                    - Controlled complaint textarea (pre-filled from queue)
 *                    - Investigation results with urgency badge
 *
 * All network calls go through lib/api.ts. No fetch() calls here.
 */

import { useState } from "react";
import { postInvestigate } from "@/lib/api";
import type { InvestigationResult, QueuedComplaint, TriageCategory } from "@/lib/types";
import ComplaintQueue from "@/components/ComplaintQueue";
import ComplaintInput from "@/components/ComplaintInput";
import ResultsPanel from "@/components/ResultsPanel";
import WorkflowStepper from "@/components/WorkflowStepper";

// ---------------------------------------------------------------------------
// Hardcoded complaint queue
// ---------------------------------------------------------------------------

const COMPLAINTS: QueuedComplaint[] = [
  {
    id: "c1",
    clientId: "Client #4821",
    category: "Institutional Delay",
    text: "Client transferred their RRSP from TD Bank 3 weeks ago. Status shows Transferring but nothing has arrived. Client says TD confirmed funds left their account 2 weeks ago.",
  },
  {
    id: "c2",
    clientId: "Client #3307",
    category: "Wire Transfer Issue",
    text: "Client sent a wire transfer yesterday morning, received same-day confirmation email, funds still not showing in account after 24 hours.",
  },
  {
    id: "c3",
    clientId: "Client #5512",
    category: "Missing Funds",
    text: "Client initiated a PAD deposit of $4,500 six business days ago. Bank confirms debit was taken but funds are not reflected in Wealthsimple balance.",
  },
  {
    id: "c4",
    clientId: "Client #2198",
    category: "Account Restriction",
    text: "Client account was flagged and restricted after a large TFSA transfer. Client has not received any communication and cannot access their account.",
  },
  {
    id: "c5",
    clientId: "Client #6643",
    category: "Transfer Rejected",
    text: "Client attempted to move TFSA from RBC. Transfer was rejected but client was not notified. Discovered only after checking status in app.",
  },
];

const TRIAGE_BADGE_COLORS: Record<TriageCategory, string> = {
  "Institutional Delay": "bg-amber-100 text-amber-700 border border-amber-200",
  "Wire Transfer Issue": "bg-blue-100 text-blue-700 border border-blue-200",
  "Missing Funds": "bg-red-100 text-ws-red border border-red-200",
  "Account Restriction": "bg-red-100 text-ws-red border border-red-200",
  "Transfer Rejected": "bg-amber-100 text-amber-700 border border-amber-200",
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Home() {
  const [activeComplaint, setActiveComplaint] = useState<QueuedComplaint | null>(null);
  const [complaint, setComplaint] = useState("");
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(1);
  const [reviewedIds, setReviewedIds] = useState<Set<string>>(new Set());

  function handleSelectComplaint(c: QueuedComplaint) {
    setActiveComplaint(c);
    setComplaint(c.text);
    setResult(null);
    setError(null);
    setStep(1);
  }

  async function handleInvestigate() {
    if (!complaint.trim() || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setStep(2); // → AI Analysis

    try {
      const data = await postInvestigate({ complaint: complaint.trim() });
      setResult(data);
      setStep(3); // → Draft Ready
      if (activeComplaint) {
        setReviewedIds((prev) => new Set([...prev, activeComplaint.id]));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStep(1); // Reset stepper on error
    } finally {
      setLoading(false);
    }
  }

  function handleApprove() {
    setStep(4); // → Agent Review
    setTimeout(() => setStep(5), 600); // → Resolved

    // Human approval checkpoint — non-functional in this demo.
    console.log("[approval] Draft approved by agent.", {
      complaint: complaint.slice(0, 100),
      failure_point: result?.failure_point,
      confidence: result?.confidence_score,
      timestamp: new Date().toISOString(),
    });
  }

  return (
    <div className="h-screen flex flex-col bg-white overflow-hidden">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="border-b border-ws-border px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-5 h-5 bg-dune rounded-full" />
          <span className="text-sm font-bold tracking-tight text-dune">
            Wealthsimple
          </span>
          <span className="text-ws-border mx-1.5 select-none">|</span>
          <span className="text-sm font-semibold text-dune">
            Transfer Investigation
          </span>
        </div>
        <span className="text-[10px] font-bold tracking-[0.07em] uppercase bg-gold text-dune px-2 py-0.5 rounded">
          Internal ops tool
        </span>
      </header>

      {/* ── Body ───────────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── Left panel: Complaint Queue ────────────────────────────── */}
        <ComplaintQueue
          complaints={COMPLAINTS}
          activeId={activeComplaint?.id ?? null}
          reviewedIds={reviewedIds}
          onSelect={handleSelectComplaint}
        />

        {/* ── Right panel: Investigation Workspace ───────────────────── */}
        <main className="flex-1 overflow-y-auto px-8 py-6">

          {/* Workspace header */}
          <div className="flex items-start justify-between mb-5 gap-4">
            <div>
              <h2 className="text-lg font-bold tracking-tight text-dune">
                {activeComplaint
                  ? activeComplaint.clientId
                  : "Investigation Workspace"}
              </h2>
              <p className="text-xs text-gray-ws mt-0.5">
                {activeComplaint
                  ? "Review the complaint below, then click Investigate"
                  : "Select a complaint from the queue to begin"}
              </p>
            </div>
            {activeComplaint && (
              <span
                className={`text-[11px] font-semibold px-2.5 py-1 rounded shrink-0 ${TRIAGE_BADGE_COLORS[activeComplaint.category]}`}
              >
                {activeComplaint.category}
              </span>
            )}
          </div>

          {/* Workflow stepper */}
          <WorkflowStepper step={step} />

          {/* Complaint textarea */}
          <ComplaintInput
            value={complaint}
            onChange={setComplaint}
            onInvestigate={handleInvestigate}
            loading={loading}
          />

          {/* Loading indicator */}
          {loading && (
            <div className="text-center py-10 text-gray-ws text-sm">
              <span className="inline-block w-4 h-4 border-2 border-ws-border border-t-dune rounded-full animate-spin align-middle mr-2" />
              Running investigation — this may take a few seconds…
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-[#FDF2F2] border border-[#E8C4C4] border-l-[3px] border-l-ws-red rounded px-4 py-3 text-ws-red text-sm mb-4">
              Error: {error}
            </div>
          )}

          {/* Results */}
          {result && !loading && (
            <ResultsPanel result={result} onApprove={handleApprove} />
          )}
        </main>
      </div>
    </div>
  );
}
