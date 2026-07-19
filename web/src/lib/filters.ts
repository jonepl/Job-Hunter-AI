// The status-view filters (W3). The job list is one cached ['jobs'] array; these
// predicates split it into the triage queue, the in-flight pipeline, and the full
// list — client-side, so switching is instant and every count shares one source of
// truth. Reuses statusGroup() from status.ts so the "active" definition lives once.

import type { JobSummary } from "../api/client";
import { statusGroup } from "./status";

export type JobFilterId = "triage" | "pipeline" | "all" | "saved";

/** The view a freshly opened list lands on — the undecided triage queue. */
export const DEFAULT_FILTER: JobFilterId = "triage";

export interface JobFilter {
  id: JobFilterId;
  label: string;
  predicate: (job: JobSummary) => boolean;
}

/** The filter chips, in display order. Terminal/offer jobs live under "All". */
export const JOB_FILTERS: JobFilter[] = [
  {
    id: "triage",
    label: "Triage",
    // Undecided machine states awaiting a human decision.
    predicate: (job) => job.status === "new" || job.status === "evaluated",
  },
  {
    id: "pipeline",
    label: "Pipeline",
    // In-flight applications: applied, started, interviewing.
    predicate: (job) => statusGroup(job.status) === "active",
  },
  {
    id: "all",
    label: "All",
    predicate: () => true,
  },
  {
    id: "saved",
    label: "Saved",
    predicate: (job) => job.saved === true,
  },
];

function filterFor(id: JobFilterId): JobFilter {
  const filter = JOB_FILTERS.find((entry) => entry.id === id);
  if (!filter) {
    throw new Error(`Unknown job filter: ${id}`);
  }
  return filter;
}

/** Apply a filter, preserving the API's strongest-first order. */
export function filterJobs(jobs: JobSummary[], id: JobFilterId): JobSummary[] {
  return jobs.filter(filterFor(id).predicate);
}

/** Count the jobs matching a filter — for the per-chip and active/total counts. */
export function countFor(jobs: JobSummary[], id: JobFilterId): number {
  return jobs.reduce((total, job) => total + (filterFor(id).predicate(job) ? 1 : 0), 0);
}
