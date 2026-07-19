import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type ResumeState } from "../api/client";

/** Query key for the master-resume panel state (active + version history). */
export const resumeQueryKey = ["resume"] as const;

/** Fetch the master-resume state — active version plus history. */
export function useResume() {
  return useQuery<ResumeState>({
    queryKey: resumeQueryKey,
    queryFn: api.getResume,
  });
}

// Upload and activate are NOT optimistic: an upload's parse result (version,
// counts, whether identical bytes reactivate an existing version) is unknown
// until the server responds, so we invalidate on success and let the fresh state
// win. `isPending` / `error` drive the panel's parse-status feedback.

/** Upload (or replace) the master resume; refresh the panel on success. */
export function useUploadResume() {
  const qc = useQueryClient();
  return useMutation<ResumeState, Error, File>({
    mutationFn: (file) => api.uploadResume(file),
    onSuccess: (state) => qc.setQueryData(resumeQueryKey, state),
  });
}

/** Restore an earlier stored version as the active one. */
export function useActivateResumeVersion() {
  const qc = useQueryClient();
  return useMutation<ResumeState, Error, number>({
    mutationFn: (version) => api.activateResumeVersion(version),
    onSuccess: (state) => qc.setQueryData(resumeQueryKey, state),
  });
}
