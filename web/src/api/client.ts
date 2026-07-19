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
export type SettingsOut = components["schemas"]["SettingsOut"];
export type SettingsUpdate = components["schemas"]["SettingsUpdate"];
export type SecretStatus = components["schemas"]["SecretStatus"];
export type SchedulePreview = components["schemas"]["SchedulePreview"];
export type ProfileOut = components["schemas"]["ProfileOut"];
export type ProfileIn = components["schemas"]["ProfileIn"];
export type RunOut = components["schemas"]["RunOut"];
export type RunStatus = RunOut["status"];

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
  // 204 No Content (e.g. DELETE) has no body to parse.
  if (res.status === 204) {
    return undefined as T;
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
  getSettings: () => request<SettingsOut>("/api/settings"),
  updateSettings: (body: SettingsUpdate) =>
    request<SettingsOut>("/api/settings", { method: "PUT", body }),
  setSecret: (name: string, value: string) =>
    request<SecretStatus>(`/api/settings/secrets/${name}`, {
      method: "PUT",
      body: { value },
    }),
  clearSecret: (name: string) =>
    request<SecretStatus>(`/api/settings/secrets/${name}`, { method: "DELETE" }),
  getSchedulePreview: (cron: string, timezone: string) =>
    request<SchedulePreview>(
      `/api/settings/schedule/preview?cron=${encodeURIComponent(cron)}&timezone=${encodeURIComponent(timezone)}`,
    ),
  listProfiles: () => request<ProfileOut[]>("/api/profiles"),
  createProfile: (body: ProfileIn) =>
    request<ProfileOut>("/api/profiles", { method: "POST", body }),
  updateProfile: (id: number, body: ProfileIn) =>
    request<ProfileOut>(`/api/profiles/${id}`, { method: "PUT", body }),
  deleteProfile: (id: number) =>
    request<void>(`/api/profiles/${id}`, { method: "DELETE" }),
  startRun: () => request<RunOut>("/api/runs", { method: "POST" }),
  getRun: (id: string) => request<RunOut>(`/api/runs/${id}`),
  listRuns: () => request<RunOut[]>("/api/runs"),
};

/**
 * The download URL for a ready generation. Used as a plain anchor href so the
 * browser streams the .docx to disk — the document bytes never pass through JS,
 * keeping generated content out of the DOM (ADR-034 §3, ui-spec §7).
 */
export const generationDownloadUrl = (id: string): string =>
  `/api/generations/${id}/download`;
