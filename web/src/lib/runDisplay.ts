// Run-status display vocabulary, shared by the run-history rail (Part C.3) and the
// run-state panels (Part F) so the dot colour and detail line never disagree.
// `error` is a bare exception *type name*, never a message — rendered as-is.

import type { RunOut } from "../api/client";

export type RunDotColor = "accent" | "qualify" | "nearmiss" | "danger";

/** Map a run's lifecycle to its status-dot colour (semantic token name). */
export function runDotColor(run: RunOut): RunDotColor {
  if (run.status === "running") return "accent";
  if (run.status === "failed") return "danger";
  // succeeded
  return run.qualifying > 0 ? "qualify" : "nearmiss";
}

/** The mono detail line beside a run-history row. */
export function runDetailLine(run: RunOut): string {
  if (run.status === "running") return "Running…";
  if (run.status === "failed") return `Failed · ${run.error}`;
  if (run.qualifying > 0) return `${run.qualifying} matches · delivered`;
  return `Zero results · ${run.jobsFound} evaluated`;
}

/** Tailwind background classes for each dot colour (token-mapped). */
export const DOT_BG: Record<RunDotColor, string> = {
  accent: "bg-accent",
  qualify: "bg-qualify",
  nearmiss: "bg-nearmiss",
  danger: "bg-danger",
};
