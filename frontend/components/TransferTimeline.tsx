/**
 * TransferTimeline — visual step-by-step timeline for a transfer investigation.
 *
 * Renders 6 hardcoded steps representing the lifecycle of a Wealthsimple transfer.
 * Maps failure_point to the step most likely responsible for the breakdown:
 *
 *   "client"       → step 0  Transfer Requested
 *   "institution"  → step 2  Institution Processing
 *   "wealthsimple" → step 4  WS Receives Assets
 *   "unknown"      → no failure step (all steps shown as pending/muted)
 *
 * Steps before the failure step are green (completed ✓).
 * The failure step is red (✕) with a "LIKELY BREAKDOWN POINT" label.
 * Steps after the failure step are gray (pending).
 *
 * The AI-generated timeline_reconstruction prose is collapsed behind a
 * "View AI explanation" disclosure button (collapsed by default).
 *
 * Layout: horizontal on md+ screens, vertical on mobile.
 * All colours use the project's Tailwind brand tokens (dune, gold, ws-red, etc.).
 */

"use client";

import { useState } from "react";
import type { FailurePoint } from "@/lib/types";
import RichText from "@/components/RichText";

interface Props {
  failure_point: FailurePoint;
  timeline_reconstruction: string;
}

const STEPS = [
  "Transfer Requested",
  "WS Sends to Institution",
  "Institution Processing",
  "Assets in Transit",
  "WS Receives Assets",
  "Client Confirmation",
];

const FAILURE_IDX: Record<FailurePoint, number | null> = {
  client:       0,
  institution:  2,
  wealthsimple: 4,
  unknown:      null,
};

type StepState = "completed" | "failed" | "pending";

function getStepState(i: number, failureIdx: number | null): StepState {
  if (failureIdx === null) return "pending";
  if (i < failureIdx)     return "completed";
  if (i === failureIdx)   return "failed";
  return "pending";
}

const CIRCLE_CLASS: Record<StepState, string> = {
  completed: "bg-emerald-500 border-emerald-500 text-white",
  failed:    "bg-ws-red border-ws-red text-white",
  pending:   "bg-white border-ws-border text-gray-ws",
};

const LABEL_CLASS: Record<StepState, string> = {
  completed: "text-dune",
  failed:    "text-ws-red font-semibold",
  pending:   "text-gray-ws",
};

export default function TransferTimeline({
  failure_point,
  timeline_reconstruction,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const failureIdx = FAILURE_IDX[failure_point];

  return (
    <div>
      {/* ── Step track ─────────────────────────────────────────────── */}
      {/* Desktop: horizontal flex. Mobile: vertical flex. */}
      <div className="flex flex-col md:flex-row md:items-start gap-0">
        {STEPS.map((label, i) => {
          const state = getStepState(i, failureIdx);
          const isLast = i === STEPS.length - 1;
          // Connector after this step is emerald only when this step completed
          const connectorClass =
            state === "completed" ? "bg-emerald-500" : "bg-ws-border";

          return (
            <div
              key={label}
              className={`flex md:flex-col md:items-center ${!isLast ? "md:flex-1" : ""}`}
            >
              {/* Circle row (desktop: circle + horizontal connector) */}
              <div className="flex md:flex-row flex-col items-center w-full">
                {/* Circle */}
                <div
                  className={`w-7 h-7 rounded-full border-2 flex items-center justify-center text-[11px] font-bold shrink-0 ${CIRCLE_CLASS[state]}`}
                >
                  {state === "completed" && "✓"}
                  {state === "failed"    && "✕"}
                  {state === "pending"   && (
                    <span className="w-1.5 h-1.5 rounded-full bg-ws-border block" />
                  )}
                </div>

                {/* Horizontal connector (desktop only, not after last step) */}
                {!isLast && (
                  <div className={`hidden md:block flex-1 h-px mt-0 ${connectorClass}`} />
                )}

                {/* Vertical connector (mobile only, not after last step) */}
                {!isLast && (
                  <div className={`md:hidden w-px h-5 ml-3 ${connectorClass}`} />
                )}
              </div>

              {/* Label + breakdown badge */}
              <div className="md:mt-2 ml-3 md:ml-0 md:text-center pb-3 md:pb-0">
                <p
                  className={`text-[10px] leading-tight md:max-w-[72px] ${LABEL_CLASS[state]}`}
                >
                  {label}
                </p>
                {state === "failed" && (
                  <span className="inline-block text-[8px] font-bold tracking-widest uppercase text-ws-red mt-0.5 leading-tight">
                    LIKELY BREAKDOWN
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Collapsible AI explanation ──────────────────────────────── */}
      <div className="mt-4 border-t border-ws-border pt-3">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-xs font-semibold text-gray-ws hover:text-dune transition-colors"
        >
          <span className="text-[10px]">{expanded ? "▾" : "▸"}</span>
          <span>{expanded ? "Hide AI explanation" : "View AI explanation"}</span>
        </button>

        {expanded && (
          <p className="mt-3 text-sm text-dune leading-relaxed">
            <RichText text={timeline_reconstruction} />
          </p>
        )}
      </div>
    </div>
  );
}
