/**
 * ConfidenceScore — visual confidence bar + numeric label.
 *
 * score: 0.0–1.0  (maps to 0%–100%)
 * Color thresholds:
 *   ≥ 0.75 → green (high)
 *   ≥ 0.50 → amber (medium)
 *   <  0.50 → red   (low)
 */

interface Props {
  score: number;
}

function barColor(score: number): string {
  if (score >= 0.75) return "bg-emerald-500";
  if (score >= 0.5) return "bg-amber-400";
  return "bg-ws-red";
}

function label(score: number): string {
  if (score >= 0.75) return "High";
  if (score >= 0.5) return "Medium";
  return "Low";
}

export default function ConfidenceScore({ score }: Props) {
  const pct = Math.round(score * 100);

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-semibold text-dune uppercase tracking-wide">
          Confidence
        </span>
        <span className="text-xs text-gray-ws">
          {label(score)} — {pct}%
        </span>
      </div>
      <div className="h-2 bg-ws-border rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${barColor(score)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
