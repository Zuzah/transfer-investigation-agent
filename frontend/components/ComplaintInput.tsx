/**
 * ComplaintInput — textarea + submit button.
 *
 * Stateless: the parent (page.tsx) owns the complaint string and loading flag.
 * onInvestigate fires with the trimmed complaint text on submit.
 */

"use client";

import { useState } from "react";

interface Props {
  onInvestigate: (complaint: string) => void;
  loading: boolean;
}

export default function ComplaintInput({ onInvestigate, loading }: Props) {
  const [text, setText] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    onInvestigate(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} className="mb-8">
      <label
        htmlFor="complaint"
        className="block text-sm font-semibold text-dune mb-2"
      >
        Complaint
      </label>
      <textarea
        id="complaint"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={6}
        placeholder="Paste the client's complaint or transfer issue here…"
        disabled={loading}
        className="w-full border border-ws-border rounded px-4 py-3 text-sm text-dune placeholder-gray-ws resize-y focus:outline-none focus:ring-2 focus:ring-gold focus:border-gold disabled:opacity-50 disabled:cursor-not-allowed"
      />
      <button
        type="submit"
        disabled={loading || !text.trim()}
        className="mt-3 bg-dune text-white text-sm font-semibold px-6 py-2.5 rounded hover:bg-opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {loading ? "Investigating…" : "Investigate"}
      </button>
    </form>
  );
}
