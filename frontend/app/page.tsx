"use client";

/**
 * Investigation page — the single route of this app.
 *
 * Owns top-level state (loading, error, result) and passes callbacks down
 * to child components. No fetch calls here — all network calls go through
 * lib/api.ts.
 */

import { useState } from "react";
import { postInvestigate } from "@/lib/api";
import type { InvestigationResult } from "@/lib/types";
import ComplaintInput from "@/components/ComplaintInput";
import ResultsPanel from "@/components/ResultsPanel";

export default function Home() {
  const [complaint, setComplaint] = useState("");
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleInvestigate(text: string) {
    setComplaint(text);
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await postInvestigate({ complaint: text });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  function handleApprove() {
    // Human approval checkpoint — non-functional in this demo.
    console.log("[approval] Agent reviewed and approved draft response.", {
      complaint: complaint.slice(0, 100),
      failure_point: result?.failure_point,
      confidence: result?.confidence_score,
      timestamp: new Date().toISOString(),
    });
    alert(
      "Draft marked as approved.\n\n" +
        "In production this would trigger the send workflow. " +
        "The approval has been logged to the console."
    );
  }

  return (
    <div className="min-h-screen bg-white py-12 px-4">
      <div className="max-w-[800px] mx-auto">

        {/* ── Header ──────────────────────────────────────────────────── */}
        <header className="mb-12 border-b border-ws-border pb-6">
          <div className="flex items-center gap-2.5 mb-4">
            <div className="w-7 h-7 bg-dune rounded-full" />
            <span className="text-base font-bold tracking-tight text-dune">
              Wealthsimple
            </span>
          </div>
          <h1 className="text-[2rem] font-bold tracking-[-0.03em] text-dune leading-[1.15]">
            Transfer Investigation
          </h1>
          <p className="mt-2 text-sm text-gray-ws">
            Retrieve, analyse, and draft — all responses require human review
            before sending.
          </p>
          <span className="inline-flex items-center mt-3 bg-gold text-dune text-xs font-bold tracking-[0.05em] uppercase px-2.5 py-1 rounded">
            Internal ops tool
          </span>
        </header>

        {/* ── Complaint Input ─────────────────────────────────────────── */}
        <ComplaintInput onInvestigate={handleInvestigate} loading={loading} />

        {/* ── Loading indicator ───────────────────────────────────────── */}
        {loading && (
          <div className="text-center py-12 text-gray-ws text-sm">
            <span className="inline-block w-5 h-5 border-2 border-ws-border border-t-dune rounded-full animate-spin align-middle mr-2.5" />
            Investigating — this may take a few seconds…
          </div>
        )}

        {/* ── Error display ───────────────────────────────────────────── */}
        {error && (
          <div className="bg-[#FDF2F2] border border-[#E8C4C4] border-l-[3px] border-l-ws-red rounded px-4 py-3.5 text-ws-red text-sm mb-4">
            Error: {error}
          </div>
        )}

        {/* ── Results ─────────────────────────────────────────────────── */}
        {result && !loading && (
          <ResultsPanel result={result} onApprove={handleApprove} />
        )}
      </div>
    </div>
  );
}
