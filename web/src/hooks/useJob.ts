import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type HumanStatus, type JobDetail, type JobSummary } from "../api/client";
import { jobsQueryKey } from "./useJobs";

/** Query key for a single job's detail (ui-spec §8). */
export const jobQueryKey = (id: number) => ["job", id] as const;

/** Fetch one job's detail fan-out. Disabled until an id is selected. */
export function useJob(id: number | null) {
  return useQuery<JobDetail>({
    queryKey: jobQueryKey(id ?? -1),
    queryFn: () => api.getJob(id as number),
    enabled: id !== null,
  });
}

// Both mutations below are optimistic (ui-spec §8): patch the ['job', id] and
// ['jobs'] caches immediately, roll back on error, and invalidate both on settle
// so the server's fresh copy wins. The card in the list and the detail pane stay
// in lockstep without a refetch round-trip.

interface StatusVars {
  status: HumanStatus;
  note?: string;
}

/** Optimistically mark a job's status, rolling back on error. */
export function useMarkStatus(id: number) {
  const qc = useQueryClient();
  return useMutation<JobDetail, Error, StatusVars, OptimisticCtx>({
    mutationFn: ({ status, note }) => api.markStatus(id, status, note),
    onMutate: (vars) => patchCaches(qc, id, { status: vars.status }),
    onError: (_err, _vars, ctx) => rollback(qc, id, ctx),
    onSettled: () => invalidate(qc, id),
  });
}

/** Optimistically toggle a job's saved bookmark, rolling back on error. */
export function useSaved(id: number) {
  const qc = useQueryClient();
  return useMutation<JobDetail, Error, boolean, OptimisticCtx>({
    mutationFn: (saved) => api.setSaved(id, saved),
    onMutate: (saved) => patchCaches(qc, id, { saved }),
    onError: (_err, _vars, ctx) => rollback(qc, id, ctx),
    onSettled: () => invalidate(qc, id),
  });
}

interface OptimisticCtx {
  prevJob?: JobDetail;
  prevList?: JobSummary[];
}

type JobPatch = Partial<Pick<JobDetail, "status" | "saved">>;

function patchCaches(
  qc: ReturnType<typeof useQueryClient>,
  id: number,
  patch: JobPatch,
): OptimisticCtx {
  qc.cancelQueries({ queryKey: jobQueryKey(id) });
  qc.cancelQueries({ queryKey: jobsQueryKey });

  const prevJob = qc.getQueryData<JobDetail>(jobQueryKey(id));
  const prevList = qc.getQueryData<JobSummary[]>(jobsQueryKey);

  if (prevJob) qc.setQueryData<JobDetail>(jobQueryKey(id), { ...prevJob, ...patch });
  if (prevList) {
    qc.setQueryData<JobSummary[]>(
      jobsQueryKey,
      prevList.map((j) => (j.id === id ? { ...j, ...patch } : j)),
    );
  }
  return { prevJob, prevList };
}

function rollback(
  qc: ReturnType<typeof useQueryClient>,
  id: number,
  ctx: OptimisticCtx | undefined,
): void {
  if (ctx?.prevJob) qc.setQueryData(jobQueryKey(id), ctx.prevJob);
  if (ctx?.prevList) qc.setQueryData(jobsQueryKey, ctx.prevList);
}

function invalidate(qc: ReturnType<typeof useQueryClient>, id: number): void {
  qc.invalidateQueries({ queryKey: jobQueryKey(id) });
  qc.invalidateQueries({ queryKey: jobsQueryKey });
}
