// The Search filter model (redesign Part D.2). It replaces the old single-select
// "view" with multi-select label chips OR-ed together, plus two independent AND-ed
// toggles: a "Saved" bookmark filter and a "Qualifying only" score filter. All
// selection is React state in the parent, never browser storage (design.md).

import type { HumanStatus, JobSummary } from "../api/client";
import { scoreState } from "./score";

export interface FilterState {
  /** Human-set statuses OR-ed together; empty = no label constraint. */
  labels: HumanStatus[];
  /** AND-ed: only jobs whose own score qualifies (per-job threshold). */
  qualifyingOnly: boolean;
  /** AND-ed: only bookmarked jobs (conflict #10 — Saved kept as a filter). */
  saved: boolean;
}

/** A freshly opened list applies no constraint — every job shows. */
export const EMPTY_FILTER: FilterState = {
  labels: [],
  qualifyingOnly: false,
  saved: false,
};

/** The four status chips, in display order (Saved + Qualifying are separate). */
export const LABEL_CHIPS: { status: HumanStatus; label: string }[] = [
  { status: "applied", label: "Applied" },
  { status: "started", label: "Started" },
  { status: "interviewing", label: "Interviewing" },
  { status: "not_interested", label: "Not interested" },
];

/** Whether a job qualifies against its own threshold (never a global one). */
function qualifies(job: JobSummary): boolean {
  return scoreState(job.score, job.threshold, job.nearMissFloor) === "qualify";
}

/** Apply the full filter: labels OR-ed, Saved and Qualifying AND-ed on top. */
export function applyFilters(jobs: JobSummary[], filter: FilterState): JobSummary[] {
  return jobs.filter((job) => {
    if (filter.labels.length > 0 && !filter.labels.includes(job.status as HumanStatus)) {
      return false;
    }
    if (filter.saved && !job.saved) return false;
    if (filter.qualifyingOnly && !qualifies(job)) return false;
    return true;
  });
}

/** True when any constraint is active — drives the Clear affordance's visibility. */
export function isFilterActive(filter: FilterState): boolean {
  return filter.labels.length > 0 || filter.qualifyingOnly || filter.saved;
}

/** Toggle one status label in/out of the set (immutably). */
export function toggleLabel(filter: FilterState, status: HumanStatus): FilterState {
  const labels = filter.labels.includes(status)
    ? filter.labels.filter((s) => s !== status)
    : [...filter.labels, status];
  return { ...filter, labels };
}

// --- Counts, always drawn from the UNFILTERED base list so a chip never reads 0
//     while its rows are on screen (design lines 118–128). ---

/** Count jobs carrying a given status in the base (unfiltered) list. */
export function labelCount(jobs: JobSummary[], status: HumanStatus): number {
  return jobs.reduce((n, job) => n + (job.status === status ? 1 : 0), 0);
}

/** Count bookmarked jobs in the base list. */
export function savedCount(jobs: JobSummary[]): number {
  return jobs.reduce((n, job) => n + (job.saved ? 1 : 0), 0);
}

/** Count qualifying jobs in the base list. */
export function qualifyingCount(jobs: JobSummary[]): number {
  return jobs.reduce((n, job) => n + (qualifies(job) ? 1 : 0), 0);
}
