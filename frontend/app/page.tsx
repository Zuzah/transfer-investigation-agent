"use client";

/**
 * Landing page — role chooser.
 *
 * Three cards that route to the three role-specific views:
 *   /client   — client submits a transfer complaint
 *   /analyst  — ops analyst investigates cases and takes action
 *   /admin    — admin resets the demo database
 */

import Link from "next/link";

const ROLES = [
  {
    href: "/client",
    label: "Client",
    sublabel: "Submit a transfer complaint",
    description: "Report a stuck or failed transfer and track your case status.",
    badge: "Client view",
    badgeClass: "bg-blue-100 text-blue-700 border-blue-200",
    iconBg: "bg-blue-50",
    icon: (
      <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
      </svg>
    ),
  },
  {
    href: "/analyst",
    label: "Analyst",
    sublabel: "Investigate and resolve cases",
    description: "Review the complaint queue, run AI analysis, and approve or escalate.",
    badge: "Internal ops",
    badgeClass: "bg-gold text-dune border-amber-200",
    iconBg: "bg-amber-50",
    icon: (
      <svg className="w-6 h-6 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
    ),
  },
  {
    href: "/admin",
    label: "Admin",
    sublabel: "Database operations",
    description: "Reset the demo database, view case counts, and re-seed demo data.",
    badge: "Admin only",
    badgeClass: "bg-gray-100 text-gray-ws border-ws-border",
    iconBg: "bg-gray-50",
    icon: (
      <svg className="w-6 h-6 text-gray-ws" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
      </svg>
    ),
  },
] as const;

export default function Home() {
  return (
    <div className="min-h-screen bg-white flex flex-col">

      {/* Header */}
      <header className="border-b border-ws-border px-6 py-3 flex items-center gap-2.5">
        <div className="w-5 h-5 bg-dune rounded-full" />
        <span className="text-sm font-bold tracking-tight text-dune">Wealthsimple</span>
        <span className="text-ws-border mx-1.5 select-none">|</span>
        <span className="text-sm font-semibold text-dune">Transfer Investigation</span>
        <span className="ml-auto text-[10px] font-bold tracking-[0.07em] uppercase bg-gold text-dune px-2 py-0.5 rounded">
          Internal ops tool
        </span>
      </header>

      {/* Body */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-16">
        <div className="max-w-2xl w-full text-center mb-10">
          <h1 className="text-2xl font-bold tracking-tight text-dune mb-2">
            Select your role
          </h1>
          <p className="text-sm text-gray-ws">
            This is an internal demo. Choose the perspective you want to explore.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl w-full">
          {ROLES.map((role) => (
            <Link
              key={role.href}
              href={role.href}
              className="group flex flex-col rounded-lg border border-ws-border bg-white px-5 py-6 hover:border-dune hover:shadow-sm transition-all"
            >
              {/* Icon */}
              <div className={`w-10 h-10 rounded-lg ${role.iconBg} flex items-center justify-center mb-4`}>
                {role.icon}
              </div>

              {/* Label + badge */}
              <div className="flex items-center gap-2 mb-1">
                <span className="text-base font-bold text-dune">{role.label}</span>
                <span className={`text-[10px] font-semibold border px-1.5 py-0.5 rounded uppercase tracking-wide ${role.badgeClass}`}>
                  {role.badge}
                </span>
              </div>

              <p className="text-xs font-semibold text-dune mb-2">{role.sublabel}</p>
              <p className="text-xs text-gray-ws leading-relaxed">{role.description}</p>

              {/* Arrow */}
              <div className="mt-auto pt-4 text-xs font-semibold text-dune flex items-center gap-1 group-hover:gap-2 transition-all">
                Enter
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
