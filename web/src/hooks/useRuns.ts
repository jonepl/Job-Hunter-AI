import { useCallback, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type RunOut } from "../api/client";
import { jobsQueryKey } from "./useJobs";

// A run is async (W8): POST /runs starts the pipeline as a background task and
// returns a `running` record; the client polls the run until a terminal status,
// then refetches the job list to show the new results. These hooks own that
// lifecycle — the start mutation and the single-run poll. Server state via React
// Query only (no browser storage).

/** Query key for one run's live poll. */
export const runQueryKey = (id: string) => ["run", id] as const;

/**
 * The recent-runs list is keyed by scope so the rail can hold a global list and a
 * per-profile list side by side (search v2 §B). `runsBaseKey` is the shared prefix any
 * mutation invalidates to refresh *every* scope at once.
 */
export const runsBaseKey = ["runs"] as const;
export const runsQueryKey = (profileId?: number) =>
  profileId === undefined ? (["runs", "all"] as const) : (["runs", profileId] as const);

/**
 * The recent runs, newest first — global by default, or scoped to one profile when
 * `profileId` is given (the rail's per-profile history). Polls while the latest run is
 * running so the rail and the run-state panels stay live; when the latest transitions
 * out of running it invalidates the job list once so newly evaluated jobs appear.
 */
export function useRuns(profileId?: number) {
  const qc = useQueryClient();
  const key = runsQueryKey(profileId);
  return useQuery<RunOut[]>({
    queryKey: key,
    queryFn: async () => {
      const prev = qc.getQueryData<RunOut[]>(key);
      const runs = await api.listRuns(profileId);
      const wasRunning = prev?.[0]?.status === "running";
      const nowTerminal = runs[0] !== undefined && runs[0].status !== "running";
      if (wasRunning && nowTerminal) {
        qc.invalidateQueries({ queryKey: jobsQueryKey });
      }
      return runs;
    },
    refetchInterval: (query) =>
      query.state.data?.[0]?.status === "running" ? 2000 : false,
  });
}

/** True once a run has reached a terminal state (nothing left to poll). */
export function isRunDone(run: RunOut | undefined): boolean {
  return run?.status === "succeeded" || run?.status === "failed";
}

/** Start a background run. The returned `running` record seeds the poll. */
export function useStartRun() {
  return useMutation<RunOut, Error, void>({
    mutationFn: () => api.startRun(),
  });
}

/**
 * Start a background run and refresh the recent-runs list. Used by the run-state
 * panels' "Retry run" — unlike <RunButton> it doesn't own a single-run poll; the
 * shared `useRuns()` list picks the new run up on its next tick.
 */
export function useTriggerRun() {
  const qc = useQueryClient();
  return useMutation<RunOut, Error, void>({
    mutationFn: () => api.startRun(),
    onSuccess: () => qc.invalidateQueries({ queryKey: runsBaseKey }),
  });
}

/**
 * Start a background run for a single profile (the per-profile "Run now"). Shares the
 * single-flight guard with the global run, and refreshes the recent-runs list on
 * success so the rail/feed pick the new run up (per-profile-scheduling §D).
 */
export function useRunProfile() {
  const qc = useQueryClient();
  return useMutation<RunOut, Error, number>({
    mutationFn: (profileId) => api.startRun(profileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: runsBaseKey }),
  });
}

/**
 * Poll one run while it is running. The interval stops (returns false) the moment
 * the status is terminal; a successful run invalidates the job list so the newly
 * evaluated jobs appear without a manual refresh.
 */
export function useRun(id: string | null) {
  const qc = useQueryClient();
  return useQuery<RunOut>({
    queryKey: runQueryKey(id ?? ""),
    queryFn: async () => {
      const run = await api.getRun(id as string);
      if (run.status === "succeeded") {
        qc.invalidateQueries({ queryKey: jobsQueryKey });
      }
      return run;
    },
    enabled: id !== null,
    refetchInterval: (query) =>
      query.state.data?.status === "running" ? 2000 : false,
  });
}

/** Default poll cadence for the sequential batch runner (ms). */
const BATCH_POLL_MS = 1500;

/** Live progress of a client-orchestrated multi-profile run. */
export interface BatchRunState {
  /** True while the batch is in flight. */
  running: boolean;
  /** How many profiles have finished (drives "Running 2 of 3…"). */
  current: number;
  /** How many profiles the batch will run in total. */
  total: number;
  /** The exception type/message of the run that halted the batch, or null. */
  error: string | null;
}

const IDLE_BATCH: BatchRunState = { running: false, current: 0, total: 0, error: null };

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Run several profiles **sequentially**, client-orchestrated (search v2 §B, conflict #3).
 * The server's single-flight guard forbids concurrent runs, so the multi-select "Run N
 * selected" reuses that guarantee for free: fire one `POST /runs?profile=id`, poll it to
 * a terminal status, then start the next. A failed run halts the batch (its error is
 * surfaced). `pollMs` is injectable so tests don't wait real seconds.
 */
export function useRunProfilesSequentially(pollMs: number = BATCH_POLL_MS) {
  const qc = useQueryClient();
  const [state, setState] = useState<BatchRunState>(IDLE_BATCH);

  const refresh = useCallback(() => {
    qc.invalidateQueries({ queryKey: runsBaseKey });
    qc.invalidateQueries({ queryKey: jobsQueryKey });
  }, [qc]);

  const pollToTerminal = useCallback(
    async (run: RunOut): Promise<RunOut> => {
      let current = run;
      while (current.status === "running") {
        await delay(pollMs);
        current = await api.getRun(current.id);
      }
      return current;
    },
    [pollMs],
  );

  const start = useCallback(
    async (profileIds: number[]) => {
      if (profileIds.length === 0 || state.running) return;
      setState({ running: true, current: 0, total: profileIds.length, error: null });
      try {
        for (let i = 0; i < profileIds.length; i++) {
          const started = await api.startRun(profileIds[i]);
          const finished = await pollToTerminal(started);
          refresh();
          if (finished.status === "failed") {
            throw new Error(finished.error || "Run failed");
          }
          setState((s) => ({ ...s, current: i + 1 }));
        }
      } catch (err) {
        setState((s) => ({
          ...s,
          running: false,
          error: err instanceof Error ? err.message : "Run failed",
        }));
        refresh();
        return;
      }
      setState((s) => ({ ...s, running: false }));
      refresh();
    },
    [pollToTerminal, refresh, state.running],
  );

  const reset = useCallback(() => setState(IDLE_BATCH), []);

  return { ...state, start, reset };
}
