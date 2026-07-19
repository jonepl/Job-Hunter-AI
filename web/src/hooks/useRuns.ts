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
