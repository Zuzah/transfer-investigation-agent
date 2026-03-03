"use client";

/**
 * Client view — complaint submission + case status tracker.
 *
 * Pre-filled profile card (hardcoded for demo).
 * Submits to POST /cases and shows the case ID + status on success.
 * "Check case status" section lets the client poll GET /cases/{id} for updates.
 */

import Link from "next/link";
import { useState } from "react";
import { getCases, postCase } from "@/lib/api";
import type { Case, TriageCategory } from "@/lib/types";

// ---------------------------------------------------------------------------
// Hardcoded demo profile
// ---------------------------------------------------------------------------

const CLIENT_PROFILE = {
  name: "Murtaza Hasni",
  clientId: "Client #4821",
  accountType: "RRSP + TFSA",
  memberSince: "2021",
};

const CATEGORIES: TriageCategory[] = [
  "Institutional Delay",
  "Wire Transfer Issue",
  "Missing Funds",
  "Account Restriction",
  "Transfer Rejected",
];

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

const STATUS_STYLES: Record<string, string> = {
  open: "bg-blue-100 text-blue-700 border-blue-200",
  investigated: "bg-amber-100 text-amber-700 border-amber-200",
  resolved: "bg-emerald-100 text-emerald-700 border-emerald-200",
  escalated: "bg-red-100 text-ws-red border-red-200",
};

const STATUS_LABELS: Record<string, string> = {
  open: "Open — under review",
  investigated: "In progress — analyst reviewing",
  resolved: "Resolved — response sent",
  escalated: "Escalated to specialist team",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`text-[11px] font-semibold border px-2.5 py-1 rounded ${STATUS_STYLES[status] ?? "bg-gray-100 text-gray-ws border-ws-border"}`}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ClientPage() {
  const [category, setCategory] = useState<TriageCategory>("Institutional Delay");
  const [complaint, setComplaint] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submittedCase, setSubmittedCase] = useState<Case | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Status check
  const [statusLoading, setStatusLoading] = useState(false);
  const [checkedCase, setCheckedCase] = useState<Case | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!complaint.trim() || submitting) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const c = await postCase({
        client_id: CLIENT_PROFILE.clientId,
        category,
        complaint: complaint.trim(),
      });
      setSubmittedCase(c);
      setComplaint("");
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCheckStatus() {
    if (!submittedCase) return;
    setStatusLoading(true);
    setStatusError(null);
    try {
      // Fetch all cases and find the submitted one for simplicity
      const all = await getCases();
      const found = all.find((c) => c.id === submittedCase.id) ?? null;
      setCheckedCase(found);
      if (!found) setStatusError("Case not found.");
    } catch (err) {
      setStatusError(err instanceof Error ? err.message : String(err));
    } finally {
      setStatusLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">

      {/* Header */}
      <header className="border-b border-ws-border px-6 py-3 flex items-center gap-2.5 shrink-0">
        <Link href="/"><img src="/wealthsimple-logo.webp" alt="Wealthsimple" className="h-5 w-auto" /></Link>
        <span className="text-sm font-bold tracking-tight text-dune">Wealthsimple</span>
        <span className="text-ws-border mx-1.5 select-none">|</span>
        <span className="text-sm font-semibold text-dune">Transfer Support</span>
        <Link href="/" className="ml-auto text-xs text-gray-ws hover:text-dune transition-colors">
          ← Back
        </Link>
      </header>

      <div className="flex-1 max-w-xl mx-auto w-full px-6 py-10">

        {/* Profile card */}
        <div className="flex items-center gap-4 border border-ws-border rounded-lg px-5 py-4 mb-8 bg-light">
          <div className="w-10 h-10 rounded-full bg-dune flex items-center justify-center text-white text-sm font-bold shrink-0">
            {CLIENT_PROFILE.name.charAt(0)}
          </div>
          <div>
            <p className="text-sm font-bold text-dune">{CLIENT_PROFILE.name}</p>
            <p className="text-xs text-gray-ws">{CLIENT_PROFILE.clientId} · {CLIENT_PROFILE.accountType} · Member since {CLIENT_PROFILE.memberSince}</p>
          </div>
          <span className="ml-auto text-[10px] font-bold tracking-widest uppercase bg-blue-100 text-blue-700 border border-blue-200 px-2 py-0.5 rounded">
            Client view
          </span>
        </div>

        {/* Submission form */}
        {!submittedCase ? (
          <form onSubmit={handleSubmit}>
            <h2 className="text-lg font-bold tracking-tight text-dune mb-1">Report a transfer issue</h2>
            <p className="text-xs text-gray-ws mb-6">
              Tell us what happened and we&apos;ll investigate. An agent will review your case and follow up.
            </p>

            {/* Category */}
            <div className="mb-4">
              <label className="block text-[11px] font-bold text-dune uppercase tracking-wider mb-2">
                Issue type
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as TriageCategory)}
                className="w-full border border-ws-border rounded px-4 py-2.5 text-sm text-dune bg-white focus:outline-none focus:ring-2 focus:ring-gold focus:border-gold"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            {/* Complaint */}
            <div className="mb-5">
              <label className="block text-[11px] font-bold text-dune uppercase tracking-wider mb-2">
                Describe the issue
              </label>
              <textarea
                value={complaint}
                onChange={(e) => setComplaint(e.target.value)}
                rows={6}
                placeholder="e.g. I transferred my RRSP from TD Bank 3 weeks ago. The status still shows 'Transferring' but TD confirmed the funds left my account 2 weeks ago..."
                disabled={submitting}
                className="w-full border border-ws-border rounded px-4 py-3 text-sm text-dune placeholder-gray-ws resize-y focus:outline-none focus:ring-2 focus:ring-gold focus:border-gold disabled:opacity-50"
              />
            </div>

            {submitError && (
              <div className="bg-[#FDF2F2] border border-[#E8C4C4] border-l-[3px] border-l-ws-red rounded px-4 py-3 text-ws-red text-sm mb-4">
                {submitError}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting || !complaint.trim()}
              className="w-full bg-dune text-white text-[11px] font-bold tracking-widest uppercase px-5 py-3 rounded hover:bg-opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {submitting ? "Submitting…" : "Submit case"}
            </button>
          </form>
        ) : (
          /* Confirmation card */
          <div>
            <div className="border border-emerald-200 bg-emerald-50 rounded-lg px-5 py-5 mb-6">
              <div className="flex items-center gap-2 mb-3">
                <svg className="w-5 h-5 text-emerald-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                </svg>
                <h2 className="text-sm font-bold text-emerald-800">Case submitted successfully</h2>
              </div>
              <p className="text-xs text-emerald-700 mb-3">
                Your complaint has been received. An analyst will review it shortly.
              </p>
              <div className="bg-white border border-emerald-200 rounded px-4 py-3">
                <p className="text-[11px] text-gray-ws uppercase tracking-wider font-bold mb-1">Case reference</p>
                <p className="text-sm font-mono font-bold text-dune">{submittedCase.id}</p>
              </div>
            </div>

            {/* Status tracker */}
            <div className="border border-ws-border rounded-lg px-5 py-5">
              <h3 className="text-[11px] font-bold text-dune uppercase tracking-wider mb-3">Case status</h3>
              <div className="flex items-center gap-3">
                <StatusBadge status={checkedCase?.status ?? submittedCase.status} />
                <button
                  onClick={handleCheckStatus}
                  disabled={statusLoading}
                  className="text-xs font-semibold text-dune underline underline-offset-2 disabled:opacity-50"
                >
                  {statusLoading ? "Checking…" : "Refresh"}
                </button>
              </div>
              {statusError && (
                <p className="text-xs text-ws-red mt-2">{statusError}</p>
              )}
            </div>

            <button
              onClick={() => { setSubmittedCase(null); setCheckedCase(null); }}
              className="mt-6 text-xs font-semibold text-gray-ws underline underline-offset-2"
            >
              Submit another case
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
