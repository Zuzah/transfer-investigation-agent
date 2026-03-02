/**
 * RichText — inline **bold** markdown renderer.
 *
 * Splits text on **…** markers and alternates between plain <span>
 * and <strong> (font-semibold text-dune). Preserves newlines via
 * whitespace-pre-wrap on the wrapper.
 *
 * Usage:
 *   <RichText text="Transfer initiated on **2024-11-03** at **TD Bank**." />
 */

interface Props {
  text: string;
  className?: string;
}

export default function RichText({ text, className = "" }: Props) {
  // Split on ** delimiters; odd-indexed segments are bold content
  const parts = text.split("**");

  return (
    <span className={`whitespace-pre-wrap ${className}`}>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <strong key={i} className="font-semibold text-dune">
            {part}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </span>
  );
}
