/**
 * SourcesList — renders the RAG source documents cited by the agent.
 *
 * Each source is a plain string (document title / chunk identifier).
 * Renders nothing when the sources array is empty.
 */

interface Props {
  sources: string[];
}

export default function SourcesList({ sources }: Props) {
  if (sources.length === 0) return null;

  return (
    <div>
      <h3 className="text-xs font-semibold text-dune uppercase tracking-wide mb-2">
        Sources cited
      </h3>
      <ul className="space-y-1">
        {sources.map((src, i) => (
          <li
            key={i}
            className="flex items-start gap-2 text-xs text-gray-ws leading-relaxed"
          >
            <span className="mt-0.5 text-gold font-bold shrink-0">›</span>
            <span>{src}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
