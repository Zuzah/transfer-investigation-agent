/**
 * WorkflowStepper — horizontal 5-step progress tracker.
 *
 * step: 1 = Complaint Received, 2 = AI Analysis, 3 = Draft Ready,
 *       4 = Agent Review, 5 = Resolved
 *
 * Steps < current are marked complete (dark fill + checkmark).
 * Current step is highlighted gold.
 * Future steps are muted.
 */

const STEPS = [
  "Complaint Received",
  "AI Analysis",
  "Draft Ready",
  "Agent Review",
  "Resolved",
];

interface Props {
  step: number; // 1–5
}

export default function WorkflowStepper({ step }: Props) {
  return (
    <div className="flex items-start w-full mb-6">
      {STEPS.map((label, i) => {
        const n = i + 1;
        const isComplete = n < step;
        const isActive = n === step;

        return (
          <div
            key={label}
            className={`flex flex-col items-center ${i < STEPS.length - 1 ? "flex-1" : ""}`}
          >
            {/* Circle + connector line to the right */}
            <div className="flex items-center w-full">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold border-2 shrink-0 transition-colors duration-300
                  ${isComplete
                    ? "bg-dune border-dune text-white"
                    : isActive
                    ? "bg-gold border-gold text-dune"
                    : "bg-white border-ws-border text-gray-ws"}`}
              >
                {isComplete ? "✓" : n}
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`flex-1 h-px transition-colors duration-300 ${
                    n < step ? "bg-dune" : "bg-ws-border"
                  }`}
                />
              )}
            </div>

            {/* Label */}
            <span
              className={`text-[10px] mt-1.5 text-center leading-tight transition-colors duration-300
                ${isActive ? "text-dune font-semibold" : isComplete ? "text-dune" : "text-gray-ws"}`}
              style={{ maxWidth: "64px" }}
            >
              {label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
