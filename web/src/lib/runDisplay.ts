// Run-status display vocabulary, shared by the run-history rail (Part C.3) and the
// run-state panels (Part F) so the dot colour and detail line never disagree.
// `error` is a bare exception *type name*, never a message — rendered as-is.

import type { ProfileOut, RunOut } from "../api/client";
import { describeNextRun, relativeTime } from "./time";

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

// --- Per-profile status line (search v2 §C) --------------------------------

/** A profile's status dot allows a neutral "muted" state the run dots don't. */
export type ProfileDot = RunDotColor | "muted";

/** Tailwind background classes for a profile dot (adds the neutral state). */
export const PROFILE_DOT_BG: Record<ProfileDot, string> = { ...DOT_BG, muted: "bg-text-3" };

/**
 * The rail's per-profile status line — a dot + text derived from the profile's most
 * recent *per-profile* run (from the shared runs list, so no extra fetch) with a
 * fallback to schedule/paused metadata (conflict #7). Replaces the old static
 * "location · threshold" line.
 */
export function profileStatusLine(
  profile: ProfileOut,
  latest: RunOut | undefined,
): { dot: ProfileDot; text: string } {
  if (latest?.status === "running" || profile.lastRunStatus === "running") {
    return { dot: "accent", text: "Running now…" };
  }
  if (latest?.status === "succeeded") {
    return latest.qualifying > 0
      ? { dot: "qualify", text: `Delivered · ${latest.qualifying} matches` }
      : { dot: "nearmiss", text: `Zero results · ${relativeTime(latest.startedAt) ?? "recently"}` };
  }
  if (latest?.status === "failed") {
    return { dot: "danger", text: "Run failed" };
  }
  if (!profile.enabled) {
    return { dot: "muted", text: "Paused" };
  }
  if (profile.scheduleEnabled && profile.nextRunAt) {
    return { dot: "muted", text: `Next run ${describeNextRun(profile.nextRunAt) ?? "soon"}` };
  }
  return { dot: "muted", text: "Not scheduled" };
}

/** The run-history source badge: a scheduled fire vs a manual/CLI "Ad-hoc" run. */
export function runSourceLabel(run: RunOut): "Scheduled" | "Ad-hoc" {
  return run.trigger === "scheduled" ? "Scheduled" : "Ad-hoc";
}
