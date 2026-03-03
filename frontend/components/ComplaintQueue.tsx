/**
 * ComplaintQueue — left-panel list of complaint cards from the live case queue.
 *
 * Each card shows:
 *  - Client identifier + Case # (first 8 chars of UUID)
 *  - Triage category badge (color-coded by category)
 *  - First ~60 characters of the complaint text
 *  - Status badge (bottom-right): labeled dot showing the case lifecycle state
 *
 * Status lifecycle (5 states):
 *   unreviewed  — open, not yet analyzed (blue dot)
 *   in_analysis — API call in flight for this case (amber pulsing dot)
 *   draft_ready — AI response received, awaiting analyst action (gold dot)
 *   escalated   — analyst escalated the case (red dot)
 *   resolved    — analyst approved & sent response (green dot)
 *
 * Clicking a card calls onSelect with the full Case object.
 * The active card is highlighted with a gold left border.
 */

"use client";

import type { Case, TriageCategory } from "@/lib/types";

// const BADGE_COLORS: Record<TriageCategory, string> = {
//   "Institutional Delay": "bg-amber-100 text-amber-700 border-amber-200",
//   "Wire Transfer Issue": "bg-blue-100 text-blue-700 border-blue-200",
//   "Missing Funds":       "bg-red-100 text-ws-red border-red-200",
//   "Account Restriction": "bg-red-100 text-ws-red border-red-200",
//   "Transfer Rejected":   "bg-amber-100 text-amber-700 border-amber-200",
// };

const BADGE_COLORS: Record<TriageCategory, string> = {
  "Institutional Delay": "bg-amber-100 text-[rgb(126,104,18)] border-amber-200",
  "Wire Transfer Issue": "bg-amber-100 text-[rgb(126,104,18)] border-amber-200",
  "Missing Funds": "bg-amber-100 text-[rgb(126,104,18)] border-amber-200",
  "Account Restriction": "bg-amber-100 text-[rgb(126,104,18)] border-amber-200",
  "Transfer Rejected": "bg-amber-100 text-[rgb(126,104,18)] border-amber-200",
};

// ---------------------------------------------------------------------------
// UI status — 5-state lifecycle tracker
// ---------------------------------------------------------------------------

type UiStatus =
  | "unreviewed"
  | "in_analysis"
  | "draft_ready"
  | "escalated"
  | "resolved";

const STATUS_CONFIG: Record<
  UiStatus,
  { dotClass: string; label: string; labelClass: string; pulse: boolean }
> = {
  unreviewed: { dotClass: "bg-blue-500", label: "Unreviewed", labelClass: "text-blue-600", pulse: false },
  in_analysis: { dotClass: "bg-amber-400", label: "In Analysis", labelClass: "text-amber-600", pulse: true },
  draft_ready: { dotClass: "bg-gold", label: "Draft Ready", labelClass: "text-dune", pulse: false },
  escalated: { dotClass: "bg-ws-red", label: "Escalated", labelClass: "text-ws-red", pulse: false },
  resolved: { dotClass: "bg-emerald-500", label: "Resolved", labelClass: "text-emerald-600", pulse: false },
};

function getUiStatus(c: Case, investigatingId: string | null): UiStatus {
  if (c.status === "resolved") return "resolved";
  if (c.status === "escalated") return "escalated";
  if (c.status === "investigated") return "draft_ready";
  if (c.id === investigatingId) return "in_analysis";
  return "unreviewed";
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  cases: Case[];
  activeId: string | null;
  reviewedIds: Set<string>;
  investigatingId: string | null;
  onSelect: (c: Case) => void;
}

export default function ComplaintQueue({
  cases,
  activeId,
  reviewedIds,
  investigatingId,
  onSelect,
}: Props) {
  const openUnreviewed = cases.filter(
    (c) => c.status === "open" && !reviewedIds.has(c.id)
  ).length;

  return (
    <aside className="w-[30%] min-w-[260px] border-r border-ws-border flex flex-col h-full shrink-0">
      {/* Panel header */}
      <div className="px-4 py-3.5 border-b border-ws-border shrink-0">
        <h2 className="text-[11px] font-bold text-dune uppercase tracking-wider">
          Complaint Queue
        </h2>
        <p className="text-[11px] text-gray-ws mt-0.5">
          {openUnreviewed} unreviewed · {cases.length} total
        </p>
      </div>

      {/* Complaint cards */}
      <div className="flex-1 overflow-y-auto">
        {cases.length === 0 && (
          <p className="px-4 py-6 text-[11px] text-gray-ws text-center">
            No cases in queue.
          </p>
        )}
        {cases.map((c) => {
          const isActive = c.id === activeId;
          const uiStatus = getUiStatus(c, investigatingId);
          const cfg = STATUS_CONFIG[uiStatus];

          return (
            <button
              key={c.id}
              onClick={() => onSelect(c)}
              className={`w-full text-left px-4 py-3.5 border-b border-ws-border transition-colors
                ${isActive
                  ? "bg-light border-l-[3px] border-l-gold"
                  : "border-l-[3px] border-l-transparent hover:bg-[#FAFAF8]"
                }`}
            >
              {/* Client ID (dot removed from here) */}
              <p className="text-xs font-semibold text-dune mb-0.5">
                {c.client_id}
              </p>

              {/* Case # */}
              <p className="text-[10px] text-gray-ws mb-1.5">
                Case #{c.id.slice(0, 8)}
              </p>

              {/* Category badge */}
              <span
                className={`inline-block text-[10px] font-semibold border px-1.5 py-0.5 rounded mb-1.5 ${BADGE_COLORS[c.category]}`}
              >
                {c.category}
              </span>

              {/* Complaint preview */}
              <p className="text-[11px] text-gray-ws leading-relaxed">
                {c.complaint.length > 60
                  ? `${c.complaint.slice(0, 60)}…`
                  : c.complaint}
              </p>

              {/* Status badge — bottom right */}
              <div className="flex justify-end mt-1.5">
                <span className="flex items-center gap-1">
                  <span
                    className={`w-1.5 h-1.5 rounded-full shrink-0 ${cfg.dotClass}${cfg.pulse ? " animate-pulse" : ""}`}
                  />
                  <span className={`text-[10px] font-semibold ${cfg.labelClass}`}>
                    {cfg.label}
                  </span>
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
