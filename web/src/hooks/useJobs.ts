import { useQuery } from "@tanstack/react-query";

import { api, type JobSummary } from "../api/client";

/** Query key for the job list (ui-spec §8). */
export const jobsQueryKey = ["jobs"] as const;

/** Fetch the persisted job list. Server state via React Query only. */
export function useJobs() {
  return useQuery<JobSummary[]>({
    queryKey: jobsQueryKey,
    queryFn: api.listJobs,
  });
}
