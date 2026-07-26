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

/** Query key for the recent-runs list (rail + run-state panels). */
export const runsQueryKey = ["runs"] as const;

/**
 * The recent runs, newest first. Polls while the latest run is running so the rail
 * and the run-state panels stay live; when the latest transitions out of running it
 * invalidates the job list once so newly evaluated jobs appear.
 */
export function useRuns() {
  const qc = useQueryClient();
  return useQuery<RunOut[]>({
    queryKey: runsQueryKey,
    queryFn: async () => {
      const prev = qc.getQueryData<RunOut[]>(runsQueryKey);
      const runs = await api.listRuns();
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
    onSuccess: () => qc.invalidateQueries({ queryKey: runsQueryKey }),
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
    onSuccess: () => qc.invalidateQueries({ queryKey: runsQueryKey }),
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
