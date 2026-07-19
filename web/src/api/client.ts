import type { components } from "./types";

// Read models sourced from the generated OpenAPI types so they can never drift
// from the backend (ADR-033 field names).
export type JobSummary = components["schemas"]["JobSummary"];
export type JobDetail = components["schemas"]["JobDetail"];
export type ScoreCategoryRow = components["schemas"]["ScoreCategoryRow"];
export type StatusHistoryEntry = components["schemas"]["StatusHistoryEntryOut"];
export type ResumeOut = components["schemas"]["ResumeOut"];
export type ResumeState = components["schemas"]["ResumeState"];
export type GenerationOut = components["schemas"]["GenerationOut"];
export type GenerationKind = GenerationOut["kind"];
export type GenerationStatus = GenerationOut["status"];

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

/**
 * Upload a resume as multipart/form-data. Kept separate from request() because
 * the browser must set the multipart boundary itself (no JSON Content-Type), and
 * a failed parse/size check returns a clear `detail` message we surface verbatim.
 */
async function uploadResume(file: File): Promise<ResumeState> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/resume", { method: "POST", body: form });
  if (!res.ok) {
    const detail = await res
      .json()
      .then((body) => body?.detail as string | undefined)
      .catch(() => undefined);
    throw new Error(detail ?? `Upload failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as ResumeState;
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
  getResume: () => request<ResumeState>("/api/resume"),
  uploadResume,
  activateResumeVersion: (version: number) =>
    request<ResumeState>(`/api/resume/versions/${version}/activate`, {
      method: "POST",
    }),
  listJobGenerations: (jobId: number) =>
    request<GenerationOut[]>(`/api/jobs/${jobId}/generations`),
  generate: (jobId: number, kind: GenerationKind) =>
    request<GenerationOut>(`/api/jobs/${jobId}/generate`, {
      method: "POST",
      body: { kind },
    }),
  getGeneration: (id: string) => request<GenerationOut>(`/api/generations/${id}`),
};

/**
 * The download URL for a ready generation. Used as a plain anchor href so the
 * browser streams the .docx to disk — the document bytes never pass through JS,
 * keeping generated content out of the DOM (ADR-034 §3, ui-spec §7).
 */
export const generationDownloadUrl = (id: string): string =>
  `/api/generations/${id}/download`;
