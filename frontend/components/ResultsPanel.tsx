/**
 * ResultsPanel — full investigation result display.
 *
 * Renders:
 *  - Failure point badge + urgency badge (READY TO SEND / REVIEW RECOMMENDED / NEEDS REVIEW)
 *  - Confidence bar (via ConfidenceScore)
 *  - AnalystRecommendation card (recommended_action + department pills)
 *  - Timeline reconstruction (via TransferTimeline — visual step track + collapsible AI prose)
 *  - Draft client response
 *  - VerificationChecklist (category-specific pre-action steps, DB-persisted)
 *  - Escalation flags (if any)
 *  - Sources cited (via SourcesList)
 *
 * The footer Approve button prominence reflects confidence:
 *   score ≥ 0.50  → Approve & Send is primary (gold fill)
 *   score < 0.50  → Approve & Send is secondary (outlined)
 */

"use client";

import type { ReactNode } from "react";
import type { FailurePoint, InvestigationResult, TriageCategory } from "@/lib/types";
import AnalystRecommendation from "@/components/AnalystRecommendation";
import ConfidenceScore from "@/components/ConfidenceScore";
import RichText from "@/components/RichText";
import SourcesList from "@/components/SourcesList";
import TransferTimeline from "@/components/TransferTimeline";
import VerificationChecklist from "@/components/VerificationChecklist";

interface Props {
  result: InvestigationResult;
  onApprove: () => void;
  caseId: string;
  category: TriageCategory;
  onAllChecked: (v: boolean) => void;
  checklistComplete: boolean;
}

const FAILURE_LABELS: Record<FailurePoint, string> = {
  wealthsimple: "Wealthsimple",
  institution: "Receiving institution",
  client: "Client action required",
  unknown: "Unknown / needs review",
};

const FAILURE_COLORS: Record<FailurePoint, string> = {
  wealthsimple: "bg-[#FDF2F2] text-ws-red border-[#E8C4C4]",
  institution: "bg-[#FFF8E6] text-amber-700 border-amber-200",
  client: "bg-[#F0F7FF] text-blue-700 border-blue-200",
  unknown: "bg-[#F5F5F5] text-gray-ws border-ws-border",
};

function urgencyBadge(score: number): { label: string; className: string } {
  if (score >= 0.75)
    return {
      label: "READY TO SEND",
      className: "bg-emerald-100 text-emerald-700 border-emerald-200",
    };
  if (score >= 0.5)
    return {
      label: "REVIEW RECOMMENDED",
      className: "bg-amber-100 text-amber-700 border-amber-200",
    };
  return {
    label: "NEEDS REVIEW",
    className: "bg-red-100 text-ws-red border-red-200",
  };
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mb-6">
      <h3 className="text-[11px] font-bold text-dune uppercase tracking-wider mb-2">
        {title}
      </h3>
      {children}
    </div>
  );
}

export default function ResultsPanel({
  result,
  onApprove,
  caseId,
  category,
  onAllChecked,
  checklistComplete,
}: Props) {
  const {
    failure_point,
    confidence_score,
    timeline_reconstruction,
    draft_client_response,
    escalation_flags,
    sources,
    recommended_action,
    relevant_departments,
  } = result;

  const urgency = urgencyBadge(confidence_score);

  // Confidence-based CTA prominence
  const approveIsPrimary = confidence_score >= 0.5;

  const approveCls = approveIsPrimary
    ? "bg-gold text-dune text-[11px] font-bold tracking-widest uppercase px-4 py-2 rounded hover:bg-opacity-80 transition-opacity shrink-0"
    : "border border-ws-border text-dune text-[11px] font-semibold tracking-widest uppercase px-4 py-2 rounded hover:bg-light transition-colors shrink-0";

  return (
    <div className="border border-ws-border rounded-lg overflow-hidden">
      {/* ── Header bar ───────────────────────────────────────────────── */}
      <div className="bg-light border-b border-ws-border px-5 py-3.5 flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-sm font-bold text-dune tracking-tight">
          Investigation result
        </h2>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Urgency badge */}
          <span
            className={`text-[10px] font-bold tracking-widest uppercase border px-2.5 py-1 rounded ${urgency.className}`}
          >
            {urgency.label}
          </span>
          {/* Failure point badge */}
          <span
            className={`text-xs font-semibold border px-2.5 py-1 rounded ${FAILURE_COLORS[failure_point]}`}
          >
            {FAILURE_LABELS[failure_point]}
          </span>
        </div>
      </div>

      {/* ── Body ─────────────────────────────────────────────────────── */}
      <div className="px-5 py-5 space-y-6">
        {/* Confidence */}
        <ConfidenceScore score={confidence_score} />

        {/* AI recommendation */}
        <AnalystRecommendation
          recommended_action={recommended_action}
          relevant_departments={relevant_departments}
        />

        {/* Timeline */}
        <div className="mb-6">
          <h3 className="text-[11px] font-bold text-dune uppercase tracking-wider mb-3">
            Timeline reconstruction
          </h3>
          <TransferTimeline
            failure_point={failure_point}
            timeline_reconstruction={timeline_reconstruction}
          />
        </div>

        {/* Draft response */}
        <Section title="Draft client response">
          <div className="bg-light border border-ws-border rounded p-4">
            <p className="text-sm text-dune leading-relaxed">
              <RichText text={draft_client_response} />
            </p>
          </div>
        </Section>

        {/* Verification checklist */}
        <div className="mb-6">
          <VerificationChecklist
            caseId={caseId}
            category={category}
            onAllChecked={onAllChecked}
          />
        </div>

        {/* Escalation flags */}
        {escalation_flags.length > 0 && (
          <Section title="Escalation flags">
            <ul className="space-y-1">
              {escalation_flags.map((flag, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="text-ws-red font-bold shrink-0 mt-0.5">!</span>
                  <span className="text-dune">{flag}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {/* Sources */}
        <SourcesList sources={sources} />
      </div>

      {/* ── Footer / Approval ────────────────────────────────────────── */}
      <div className="bg-light border-t border-ws-border px-5 py-4 flex items-center justify-between gap-4">
        <p className="text-xs text-gray-ws">
          AI-generated — review before sending. Financial remedies require human
          authorisation.
        </p>
        <button
          onClick={onApprove}
          disabled={!checklistComplete}
          title={!checklistComplete ? "Complete verification checklist to proceed" : undefined}
          className={`${approveCls} disabled:opacity-40 disabled:cursor-not-allowed`}
        >
          Approve &amp; Send
        </button>
      </div>
    </div>
  );
}
