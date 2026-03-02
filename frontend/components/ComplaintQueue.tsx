/**
 * ComplaintQueue — left-panel list of complaint cards from the live case queue.
 *
 * Each card shows:
 *  - Client identifier + Case # (first 8 chars of UUID)
 *  - Triage category badge (color-coded by category)
 *  - First ~60 characters of the complaint text
 *  - Status dot: blue=open(unreviewed), amber=investigated, green=resolved, red=escalated
 *
 * Clicking a card calls onSelect with the full Case object.
 * The active card is highlighted with a gold left border.
 */

"use client";

import type { Case, CaseStatus, TriageCategory } from "@/lib/types";

const BADGE_COLORS: Record<TriageCategory, string> = {
  "Institutional Delay": "bg-amber-100 text-amber-700 border-amber-200",
  "Wire Transfer Issue": "bg-blue-100 text-blue-700 border-blue-200",
  "Missing Funds": "bg-red-100 text-ws-red border-red-200",
  "Account Restriction": "bg-red-100 text-ws-red border-red-200",
  "Transfer Rejected": "bg-amber-100 text-amber-700 border-amber-200",
};

const STATUS_DOT: Record<CaseStatus, string | null> = {
  open: "bg-blue-500",
  investigated: "bg-amber-400",
  resolved: "bg-emerald-500",
  escalated: "bg-ws-red",
};

const STATUS_TITLE: Record<CaseStatus, string> = {
  open: "Open",
  investigated: "Investigated — awaiting action",
  resolved: "Resolved",
  escalated: "Escalated",
};

interface Props {
  cases: Case[];
  activeId: string | null;
  reviewedIds: Set<string>;
  onSelect: (c: Case) => void;
}

export default function ComplaintQueue({
  cases,
  activeId,
  reviewedIds,
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
          const dotColor = c.status === "open" && reviewedIds.has(c.id)
            ? null
            : STATUS_DOT[c.status];

          return (
            <button
              key={c.id}
              onClick={() => onSelect(c)}
              className={`w-full text-left px-4 py-3.5 border-b border-ws-border transition-colors
                ${
                  isActive
                    ? "bg-light border-l-[3px] border-l-gold"
                    : "border-l-[3px] border-l-transparent hover:bg-[#FAFAF8]"
                }`}
            >
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-xs font-semibold text-dune">
                  {c.client_id}
                </span>
                {dotColor && (
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${dotColor}`}
                    title={STATUS_TITLE[c.status]}
                  />
                )}
              </div>
              <p className="text-[10px] text-gray-ws mb-1.5">
                Case #{c.id.slice(0, 8)}
              </p>

              <span
                className={`inline-block text-[10px] font-semibold border px-1.5 py-0.5 rounded mb-1.5 ${BADGE_COLORS[c.category]}`}
              >
                {c.category}
              </span>

              <p className="text-[11px] text-gray-ws leading-relaxed">
                {c.complaint.length > 60
                  ? `${c.complaint.slice(0, 60)}…`
                  : c.complaint}
              </p>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
