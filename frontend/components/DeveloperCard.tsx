/**
 * DeveloperCard — fixed dog-ear in the bottom-right corner of every page.
 *
 * Default state: a 40×40 gold triangle that looks like a folded page corner.
 * On hover:     the corner unfolds to reveal a small developer info card,
 *               then folds back when the cursor leaves.
 *
 * Uses CSS border-trick for the triangle (no images, no SVG).
 * Fixed positioning means it never affects layout.
 */

"use client";

import React, { useState } from "react";

const DeveloperCard: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    /*
     * The wrapper is sized to cover both the triangle and the expanded card so
     * onMouseLeave only fires when the cursor truly exits the interactive zone —
     * not when moving between the triangle and the card.
     */
    <div
      className="fixed bottom-0 right-0 z-50"
      style={{ width: "220px", height: "164px" }}
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      {/* ── Unfolded card ──────────────────────────────────────────────────── */}
      <div
        className="absolute bottom-10 right-0 w-52 rounded-lg p-4"
        style={{
          background: "#32302F",
          boxShadow: "0 8px 24px rgba(0,0,0,0.25)",
          transformOrigin: "bottom right",
          transitionProperty: "opacity, transform",
          transitionDuration: "200ms",
          transitionTimingFunction: "ease-in-out",
          opacity: isOpen ? 1 : 0,
          transform: isOpen
            ? "scale(1) translateY(0)"
            : "scale(0.95) translateY(4px)",
          pointerEvents: isOpen ? "auto" : "none",
        }}
      >
        <p
          className="text-sm font-bold mb-0.5"
          style={{ color: "#ECD06F" }}
        >
          Murtaza Hasni
        </p>
        <p className="text-[11px] mb-3" style={{ color: "rgba(255,255,255,0.55)" }}>
          Built for Wealthsimple AI Builder
        </p>

        <div className="flex flex-col gap-1.5">
          <a
            href="https://github.com/Zuzah/transfer-investigation-agent"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs hover:underline"
            style={{ color: "#ECD06F" }}
          >
            github.com/murtazahasni →
          </a>
          <a
            href="https://linkedin.com/in/murtazahasni"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs hover:underline"
            style={{ color: "#ECD06F" }}
          >
            linkedin.com/in/murtazahasni →
          </a>
        </div>
      </div>

      {/* ── Triangle (dog-ear) ─────────────────────────────────────────────── */}
      <div
        className="absolute bottom-0 right-0"
        style={{
          width: 0,
          height: 0,
          borderLeft: "40px solid transparent",
          borderBottom: "40px solid #ECD06F",
          transformOrigin: "bottom right",
          animation: isOpen ? "none" : "breathe 2.4s ease-in-out infinite",
        }}
      />
    </div>
  );
};

export default DeveloperCard;
