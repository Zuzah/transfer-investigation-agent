/**
 * ComplaintQueue — left-panel list of pre-loaded complaint cards.
 *
 * Each card shows:
 *  - Client identifier
 *  - Triage category badge (color-coded by category)
 *  - First ~60 characters of the complaint text
 *  - Blue dot when the complaint has not yet been investigated
 *
 * Clicking a card calls onSelect, which pre-fills the workspace textarea.
 * The active card (currently loaded in workspace) is highlighted with a
 * gold left border.
 */

"use client";

import type { QueuedComplaint, TriageCategory } from "@/lib/types";

const BADGE_COLORS: Record<TriageCategory, string> = {
  "Institutional Delay": "bg-amber-100 text-amber-700 border-amber-200",
  "Wire Transfer Issue": "bg-blue-100 text-blue-700 border-blue-200",
  "Missing Funds": "bg-red-100 text-ws-red border-red-200",
  "Account Restriction": "bg-red-100 text-ws-red border-red-200",
  "Transfer Rejected": "bg-amber-100 text-amber-700 border-amber-200",
};

interface Props {
  complaints: QueuedComplaint[];
  activeId: string | null;
  reviewedIds: Set<string>;
  onSelect: (complaint: QueuedComplaint) => void;
}

export default function ComplaintQueue({
  complaints,
  activeId,
  reviewedIds,
  onSelect,
}: Props) {
  const unreviewed = complaints.filter((c) => !reviewedIds.has(c.id)).length;

  return (
    <aside className="w-[30%] min-w-[260px] border-r border-ws-border flex flex-col h-full shrink-0">
      {/* Panel header */}
      <div className="px-4 py-3.5 border-b border-ws-border shrink-0">
        <h2 className="text-[11px] font-bold text-dune uppercase tracking-wider">
          Complaint Queue
        </h2>
        <p className="text-[11px] text-gray-ws mt-0.5">
          {unreviewed} unreviewed · {complaints.length} total
        </p>
      </div>

      {/* Complaint cards */}
      <div className="flex-1 overflow-y-auto">
        {complaints.map((c) => {
          const isActive = c.id === activeId;
          const isReviewed = reviewedIds.has(c.id);

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
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-dune">
                  {c.clientId}
                </span>
                {!isReviewed && (
                  <span
                    className="w-2 h-2 rounded-full bg-blue-500 shrink-0"
                    title="Unreviewed"
                  />
                )}
              </div>

              <span
                className={`inline-block text-[10px] font-semibold border px-1.5 py-0.5 rounded mb-1.5 ${BADGE_COLORS[c.category]}`}
              >
                {c.category}
              </span>

              <p className="text-[11px] text-gray-ws leading-relaxed">
                {c.text.length > 60 ? `${c.text.slice(0, 60)}…` : c.text}
              </p>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
