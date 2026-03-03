/**
 * VerificationChecklist — category-specific pre-action checklist.
 *
 * Renders 4 verification items tailored to the complaint's triage category.
 * State is persisted to the database (GET / PATCH /cases/{id}/checklist) so
 * analysts can resume where they left off after a page refresh.
 *
 * Behaviour:
 *  - On mount (or when caseId changes): fetches persisted checklist from the API
 *    and restores checked state. Missing items default to unchecked.
 *  - Toggle: updates local state immediately (optimistic UI), then persists via
 *    a 500 ms debounced PATCH call.
 *  - onAllChecked(true) fires when every item is checked; onAllChecked(false)
 *    fires whenever any item becomes unchecked.
 *
 * All colours use existing Tailwind brand tokens (dune, gold, ws-border, etc.).
 */

"use client";

import { useEffect, useRef, useState } from "react";
import type { ChecklistState, TriageCategory } from "@/lib/types";
import { getChecklist, patchChecklist } from "@/lib/api";

interface Props {
  caseId: string;
  category: TriageCategory;
  onAllChecked: (allChecked: boolean) => void;
}

// ---------------------------------------------------------------------------
// Checklist items per triage category
// ---------------------------------------------------------------------------

const CHECKLIST_ITEMS: Record<TriageCategory, string[]> = {
  "Institutional Delay": [
    "Confirm exact transfer initiation date with client",
    "Verify institution has received WS transfer request",
    "Check if securities require liquidation before transfer",
    "Confirm no prior failed attempts for this account",
  ],
  "Wire Transfer Issue": [
    "Verify wire was submitted before daily cut-off time",
    "Confirm receiving institution accepts incoming wires",
    "Check for same-day confirmation email in client record",
    "Validate destination account details are correct",
  ],
  "Missing Funds": [
    "Confirm bank debit date and amount with client",
    "Check for active funds hold on the account",
    "Verify bank account is properly linked and verified",
    "Review account for any NSF history",
  ],
  "Account Restriction": [
    "Identify trigger event for restriction",
    "Check if client has been notified via email",
    "Confirm restriction is under active review",
    "Assess if escalation to fraud team is required",
  ],
  "Transfer Rejected": [
    "Identify rejection reason from institution",
    "Confirm account type compatibility (RRSP/TFSA match)",
    "Check if client was notified of rejection",
    "Determine if resubmission is possible with corrected info",
  ],
};

export default function VerificationChecklist({ caseId, category, onAllChecked }: Props) {
  const items = CHECKLIST_ITEMS[category] ?? [];
  const [checked, setChecked] = useState<ChecklistState>({});
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Initialise all items to false
  function buildDefault(): ChecklistState {
    return Object.fromEntries(items.map((item) => [item, false]));
  }

  // Load persisted state on mount / caseId change
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const saved = await getChecklist(caseId);
        if (cancelled) return;

        // Merge: use saved values where available, default to false for missing items
        const restored: ChecklistState = buildDefault();
        for (const item of items) {
          if (item in saved) restored[item] = saved[item];
        }

        setChecked(restored);
        onAllChecked(items.every((i) => restored[i]));
      } catch {
        // Network/404 — start with all unchecked rather than blocking the UI
        if (!cancelled) {
          const defaults = buildDefault();
          setChecked(defaults);
          onAllChecked(false);
        }
      }
    }

    load();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId]);

  function toggle(item: string) {
    const next = { ...checked, [item]: !checked[item] };
    setChecked(next);
    onAllChecked(items.every((i) => next[i]));

    // Debounced persist — cancel any pending save before scheduling a new one
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      patchChecklist(caseId, next).catch(() => {
        // Persist failure is non-fatal — analyst can still action the case
      });
    }, 500);
  }

  const checkedCount = items.filter((i) => checked[i]).length;

  return (
    <div className="border border-ws-border rounded-lg p-4 bg-light">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <p className="text-[11px] font-bold text-dune uppercase tracking-wider">
          AI-suggested verification steps — complete before actioning
        </p>
        <span className="text-[10px] font-semibold text-gray-ws shrink-0 ml-2">
          {checkedCount}/{items.length}
        </span>
      </div>

      {/* Checklist items */}
      <ul className="space-y-2">
        {items.map((item) => {
          const isChecked = checked[item] ?? false;
          return (
            <li key={item} className="flex items-start gap-2.5">
              <input
                type="checkbox"
                id={`${caseId}-${item}`}
                checked={isChecked}
                onChange={() => toggle(item)}
                className="mt-0.5 h-3.5 w-3.5 shrink-0 accent-dune cursor-pointer"
              />
              <label
                htmlFor={`${caseId}-${item}`}
                className={`text-xs leading-relaxed cursor-pointer select-none transition-colors ${
                  isChecked ? "line-through text-gray-ws" : "text-dune"
                }`}
              >
                {item}
              </label>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
