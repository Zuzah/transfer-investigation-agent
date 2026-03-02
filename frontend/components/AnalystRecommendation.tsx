/**
 * AnalystRecommendation — AI-recommended next-action card.
 *
 * Colour-coded by recommended_action:
 *   send_response      → green  (✉  "Send response to client")
 *   escalate           → amber  (↑  "Escalate to a specialist team")
 *   investigate_further → red   (⚠  "Gather more information first")
 *
 * When relevant_departments is non-empty it renders department pills below
 * the headline (shown for escalate + investigate_further).
 */

import type { RecommendedAction } from "@/lib/types";

interface Props {
  recommended_action: RecommendedAction;
  relevant_departments: string[];
}

const CONFIG: Record<
  RecommendedAction,
  { border: string; bg: string; icon: string; headline: string; headlineColor: string; pillBg: string; pillText: string }
> = {
  send_response: {
    border: "border-emerald-200",
    bg: "bg-emerald-50",
    icon: "✉",
    headline: "Send response to client",
    headlineColor: "text-emerald-800",
    pillBg: "bg-emerald-100",
    pillText: "text-emerald-700",
  },
  escalate: {
    border: "border-amber-200",
    bg: "bg-amber-50",
    icon: "↑",
    headline: "Escalate to a specialist team",
    headlineColor: "text-amber-800",
    pillBg: "bg-amber-100",
    pillText: "text-amber-700",
  },
  investigate_further: {
    border: "border-red-200",
    bg: "bg-[#FDF2F2]",
    icon: "⚠",
    headline: "Gather more information first",
    headlineColor: "text-ws-red",
    pillBg: "bg-red-100",
    pillText: "text-ws-red",
  },
};

export default function AnalystRecommendation({
  recommended_action,
  relevant_departments,
}: Props) {
  const c = CONFIG[recommended_action];
  const showDepts =
    relevant_departments.length > 0 && recommended_action !== "send_response";

  return (
    <div className={`border rounded-lg px-4 py-4 ${c.border} ${c.bg}`}>
      <div className="flex items-center gap-2.5 mb-1">
        <span className={`text-base leading-none ${c.headlineColor}`} aria-hidden>
          {c.icon}
        </span>
        <span className={`text-sm font-bold ${c.headlineColor}`}>
          {c.headline}
        </span>
        <span className={`ml-auto text-[10px] font-bold tracking-widest uppercase border px-2 py-0.5 rounded ${c.border} ${c.headlineColor}`}>
          AI recommendation
        </span>
      </div>

      {showDepts && (
        <div className="flex flex-wrap gap-1.5 mt-2.5">
          {relevant_departments.map((dept) => (
            <span
              key={dept}
              className={`text-[11px] font-semibold px-2 py-0.5 rounded ${c.pillBg} ${c.pillText}`}
            >
              {dept}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
