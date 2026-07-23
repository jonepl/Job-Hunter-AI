// The job-status vocabulary shared by <StatusPill>, <StatusDropdown>, and the
// detail pane. Mirrors the backend JobStatus (ADR-025); the six human-set values
// are the only ones a person may assign (ui-spec §4).

import type { HumanStatus } from "../api/client";

/** The six selectable human-set statuses, in pipeline-then-terminal order. */
export const HUMAN_STATUSES: HumanStatus[] = [
  "applied",
  "started",
  "interviewing",
  "offer",
  "rejected",
  "not_interested",
];

/** Terminal states whose reactivation triggers the soft-confirm (ui-spec §4). */
export function isTerminalStatus(status: string): boolean {
  return status === "rejected" || status === "not_interested";
}

/** Machine statuses are never user-selectable; the dropdown shows but never offers them. */
export function isHumanStatus(status: string): status is HumanStatus {
  return (HUMAN_STATUSES as string[]).includes(status);
}

/** Humanize a status value: "not_interested" → "Not interested". */
export function statusLabel(status: string): string {
  const spaced = status.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export type StatusGroup = "machine" | "active" | "offer" | "terminal";

/** Classify a status into its visual group (ui-spec §5.2). */
export function statusGroup(status: string): StatusGroup {
  if (status === "applied" || status === "started" || status === "interviewing") {
    return "active";
  }
  if (status === "offer") return "offer";
  if (isTerminalStatus(status)) return "terminal";
  return "machine";
}

/** Whether a job belongs in the Tracked view — in-flight or an offer (Part C.1). */
export function isTracked(status: string): boolean {
  const group = statusGroup(status);
  return group === "active" || group === "offer";
}
