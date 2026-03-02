/**
 * ComplaintInput — controlled textarea + submit button.
 *
 * Value is owned by the parent (page.tsx) so that clicking a complaint card
 * in the queue can pre-fill the textarea without this component needing to
 * know about the queue.
 *
 * onChange: called on every keystroke
 * onInvestigate: called on form submit (no arguments — parent reads its own value)
 */

"use client";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onInvestigate: () => void;
  loading: boolean;
}

export default function ComplaintInput({
  value,
  onChange,
  onInvestigate,
  loading,
}: Props) {
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!value.trim() || loading) return;
    onInvestigate();
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6">
      <label
        htmlFor="complaint"
        className="block text-[11px] font-bold text-dune uppercase tracking-wider mb-2"
      >
        Complaint
      </label>
      <textarea
        id="complaint"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={5}
        placeholder="Select a complaint from the queue, or type one here…"
        disabled={loading}
        className="w-full border border-ws-border rounded px-4 py-3 text-sm text-dune placeholder-gray-ws resize-y focus:outline-none focus:ring-2 focus:ring-gold focus:border-gold disabled:opacity-50 disabled:cursor-not-allowed"
      />
      <button
        type="submit"
        disabled={loading || !value.trim()}
        className="mt-2 bg-dune text-white text-[11px] font-bold tracking-widest uppercase px-5 py-2.5 rounded hover:bg-opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {loading ? "Investigating…" : "Investigate"}
      </button>
    </form>
  );
}
