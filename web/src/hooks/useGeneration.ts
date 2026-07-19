import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type GenerationKind, type GenerationOut } from "../api/client";

// Generation is async (ui-spec §7/§8, ADR-029): a POST starts a background task and
// returns a pending record; the client polls the row until a terminal status, then
// downloads. These hooks own that lifecycle — the list of a job's generations (the
// chip's initial state), the start mutation, and the single-generation poll.

/** Query key for a job's recorded generations (the chip's starting point). */
export const jobGenerationsQueryKey = (jobId: number) =>
  ["generations", "job", jobId] as const;

/** Query key for one generation's live poll. */
export const generationQueryKey = (id: string) => ["generation", id] as const;

/** Fetch every generation recorded for a job, newest first. */
export function useJobGenerations(jobId: number) {
  return useQuery<GenerationOut[]>({
    queryKey: jobGenerationsQueryKey(jobId),
    queryFn: () => api.listJobGenerations(jobId),
  });
}

/** Start an async generation; refresh the job's list when it returns. */
export function useGenerate(jobId: number) {
  const qc = useQueryClient();
  return useMutation<GenerationOut, Error, GenerationKind>({
    mutationFn: (kind) => api.generate(jobId, kind),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: jobGenerationsQueryKey(jobId) }),
  });
}

/**
 * Poll one generation while it is pending. The interval stops (returns false) the
 * moment the status is terminal, and reaching a terminal status invalidates the
 * owning job's generation list so the persisted chip state refreshes.
 */
export function useGeneration(id: string | null, jobId: number) {
  const qc = useQueryClient();
  return useQuery<GenerationOut>({
    queryKey: generationQueryKey(id ?? ""),
    queryFn: async () => {
      const generation = await api.getGeneration(id as string);
      if (generation.status !== "pending") {
        qc.invalidateQueries({ queryKey: jobGenerationsQueryKey(jobId) });
      }
      return generation;
    },
    enabled: id !== null,
    refetchInterval: (query) =>
      query.state.data?.status === "pending" ? 1500 : false,
  });
}
