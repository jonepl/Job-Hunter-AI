import type { components } from "./types";

// The lean card model the job-list screen consumes, sourced from the generated
// OpenAPI types so it can never drift from the backend (ADR-033 field names).
export type JobSummary = components["schemas"]["JobSummary"];

/**
 * The single place fetch() is called (ui-spec §1). Uses relative URLs so the
 * same code works in dev (Vite proxies /api → :8000) and prod (same origin).
 */
async function request<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { Accept: "application/json" } });
  if (!res.ok) {
    throw new Error(`API request failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export const api = {
  listJobs: () => request<JobSummary[]>("/api/jobs"),
};
