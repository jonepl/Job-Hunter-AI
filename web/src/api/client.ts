import type { components } from "./types";

// Read models sourced from the generated OpenAPI types so they can never drift
// from the backend (ADR-033 field names).
export type JobSummary = components["schemas"]["JobSummary"];
export type JobDetail = components["schemas"]["JobDetail"];
export type ScoreCategoryRow = components["schemas"]["ScoreCategoryRow"];
export type StatusHistoryEntry = components["schemas"]["StatusHistoryEntryOut"];

// The six human-set statuses the API accepts for a write (ui-spec §4).
export type HumanStatus = components["schemas"]["StatusUpdate"]["status"];

/**
 * The single place fetch() is called (ui-spec §1). Uses relative URLs so the
 * same code works in dev (Vite proxies /api → :8000) and prod (same origin).
 */
async function request<T>(
  path: string,
  init?: { method?: string; body?: unknown },
): Promise<T> {
  const res = await fetch(path, {
    method: init?.method ?? "GET",
    headers: {
      Accept: "application/json",
      ...(init?.body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  if (!res.ok) {
    throw new Error(`API request failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export const api = {
  listJobs: () => request<JobSummary[]>("/api/jobs"),
  getJob: (id: number) => request<JobDetail>(`/api/jobs/${id}`),
  markStatus: (id: number, status: HumanStatus, note?: string) =>
    request<JobDetail>(`/api/jobs/${id}/status`, {
      method: "PATCH",
      body: { status, note: note ?? null },
    }),
  setSaved: (id: number, saved: boolean) =>
    request<JobDetail>(`/api/jobs/${id}/saved`, {
      method: "PATCH",
      body: { saved },
    }),
};
