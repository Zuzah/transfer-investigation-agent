/**
 * Application entry point.
 *
 * Owns all DOM wiring, event listeners, and render functions.
 * No fetch() calls here — all network calls go through api.ts.
 *
 * Render functions (renderFailureBadge, renderConfidence, etc.) are
 * intentionally written as pure named functions so they map 1:1 to React
 * components when the migration happens:
 *   renderFailureBadge(fp)  →  <FailureBadge failurePoint={fp} />
 *   renderConfidence(score) →  <ConfidenceBar score={score} />
 *   renderDraft(draft)      →  <DraftResponse draft={draft} />
 *   etc.
 */

import { postInvestigate } from "./api";
import type { FailurePoint, InvestigationResult } from "./types";
import "./style.css";

// ---------------------------------------------------------------------------
// DOM references — typed and resolved once at startup.
// Using non-null assertion (!) because these elements are declared in
// index.html and must exist. If an ID is wrong, the error surfaces immediately
// at runtime rather than silently as undefined.
// ---------------------------------------------------------------------------

const textarea       = document.getElementById("complaint")       as HTMLTextAreaElement;
const charHint       = document.getElementById("char-hint")       as HTMLElement;
const submitBtn      = document.getElementById("submit-btn")      as HTMLButtonElement;
const loadingEl      = document.getElementById("loading")         as HTMLElement;
const errorBox       = document.getElementById("error-box")       as HTMLElement;
const resultsEl      = document.getElementById("results")         as HTMLElement;
const failureBadge   = document.getElementById("failure-badge")   as HTMLElement;
const confidenceFill = document.getElementById("confidence-fill") as HTMLElement;
const confidencePct  = document.getElementById("confidence-pct")  as HTMLElement;
const draftBody      = document.getElementById("draft-body")      as HTMLElement;
const agentVerify    = document.getElementById("agent-verify")    as HTMLElement;
const sourcesList    = document.getElementById("sources-list")    as HTMLUListElement;
const timelineText   = document.getElementById("timeline-text")   as HTMLElement;
const flagsContainer = document.getElementById("flags-container") as HTMLElement;
const approveBtn     = document.getElementById("approve-btn")     as HTMLButtonElement;

// ---------------------------------------------------------------------------
// Character counter
// ---------------------------------------------------------------------------

function updateCharHint(): void {
  const len = textarea.value.trim().length;
  charHint.textContent = len < 20
    ? `${len}/20 characters — add ${20 - len} more`
    : `${len} characters`;
  charHint.className = len < 20 ? "char-hint warn" : "char-hint";
}

// ---------------------------------------------------------------------------
// Loading state
// ---------------------------------------------------------------------------

function setLoading(on: boolean): void {
  loadingEl.style.display = on ? "block" : "none";
  submitBtn.disabled = on;
}

// ---------------------------------------------------------------------------
// Error display
// ---------------------------------------------------------------------------

function showError(msg: string): void {
  errorBox.textContent = `Error: ${msg}`;
  errorBox.style.display = "block";
}

function clearError(): void {
  errorBox.textContent = "";
  errorBox.style.display = "none";
}

// ---------------------------------------------------------------------------
// Render helpers
// Each function is a candidate React component for the migration.
// ---------------------------------------------------------------------------

/** Maps FailurePoint literals to human-readable labels. */
const FAILURE_LABELS: Record<FailurePoint, string> = {
  wealthsimple: "Wealthsimple",
  institution:  "Institution",
  client:       "Client",
  unknown:      "Unknown",
};

function renderFailureBadge(failurePoint: FailurePoint): void {
  failureBadge.textContent = FAILURE_LABELS[failurePoint];
  failureBadge.className = `badge badge-${failurePoint}`;
}

function renderConfidence(score: number): void {
  const pct = Math.round(score * 100);
  confidenceFill.style.width = `${pct}%`;
  confidencePct.textContent = `${pct}%`;
}

function renderDraft(draft: string): void {
  // Split on the AGENT MUST VERIFY marker so it can be styled separately.
  const verifyIdx = draft.indexOf("AGENT MUST VERIFY");
  if (verifyIdx !== -1) {
    draftBody.textContent = draft.slice(0, verifyIdx).trim();
    agentVerify.textContent = draft.slice(verifyIdx).trim();
    agentVerify.style.display = "block";
  } else {
    draftBody.textContent = draft;
    agentVerify.style.display = "none";
  }
}

function renderSources(sources: string[]): void {
  sourcesList.innerHTML = "";
  sources.forEach((src) => {
    const li = document.createElement("li");
    li.textContent = src;
    sourcesList.appendChild(li);
  });
}

function renderTimeline(timeline: string): void {
  timelineText.textContent = timeline || "—";
}

function renderEscalationFlags(flags: string[]): void {
  if (flags.length === 0) {
    flagsContainer.innerHTML = '<p class="no-flags">No escalation flags raised.</p>';
    return;
  }

  flagsContainer.innerHTML = "";
  const div = document.createElement("div");
  div.className = "flags-list";
  flags.forEach((f) => {
    const chip = document.createElement("span");
    chip.className = "flag-chip";
    chip.textContent = f.replace(/_/g, " ");
    div.appendChild(chip);
  });
  flagsContainer.appendChild(div);
}

function renderResults(data: InvestigationResult): void {
  renderFailureBadge(data.failure_point);
  renderConfidence(data.confidence_score);
  renderDraft(data.draft_client_response);
  renderSources(data.sources);
  renderTimeline(data.timeline_reconstruction);
  renderEscalationFlags(data.escalation_flags);

  resultsEl.style.display = "block";
  resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---------------------------------------------------------------------------
// Approval handler
// ---------------------------------------------------------------------------

function approveDraft(): void {
  // Human approval checkpoint — non-functional in this demo.
  console.log("[approval] Agent reviewed and approved draft response.", {
    complaint:     textarea.value.trim().slice(0, 100),
    failure_point: failureBadge.textContent,
    confidence:    confidencePct.textContent,
    timestamp:     new Date().toISOString(),
  });
  alert(
    "Draft marked as approved.\n\n" +
    "In production this would trigger the send workflow. " +
    "The approval has been logged to the console."
  );
}

// ---------------------------------------------------------------------------
// Main submission handler
// ---------------------------------------------------------------------------

async function runInvestigation(): Promise<void> {
  const complaint = textarea.value.trim();

  if (complaint.length < 20) {
    charHint.textContent = "Please enter at least 20 characters before submitting.";
    charHint.className = "char-hint warn";
    textarea.focus();
    return;
  }

  setLoading(true);
  clearError();
  resultsEl.style.display = "none";

  try {
    const data = await postInvestigate({ complaint });
    renderResults(data);
  } catch (e) {
    showError(e instanceof Error ? e.message : String(e));
  } finally {
    setLoading(false);
  }
}

// ---------------------------------------------------------------------------
// Bootstrap — wire all listeners once the DOM is ready.
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  textarea.addEventListener("input", updateCharHint);
  submitBtn.addEventListener("click", runInvestigation);
  approveBtn.addEventListener("click", approveDraft);
});
