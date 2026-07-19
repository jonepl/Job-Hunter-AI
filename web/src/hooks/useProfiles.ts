import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type ProfileIn, type ProfileOut } from "../api/client";

// Search-profile CRUD state (ADR-031). Mutations invalidate the list so the editor
// and the profile picker stay in lockstep with the server.

/** Query key for the search-profile list. */
export const profilesQueryKey = ["profiles"] as const;

/** Fetch every stored search profile. */
export function useProfiles() {
  return useQuery<ProfileOut[]>({
    queryKey: profilesQueryKey,
    queryFn: api.listProfiles,
  });
}

function useInvalidateProfiles() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: profilesQueryKey });
}

/** Create a new search profile. */
export function useCreateProfile() {
  const invalidate = useInvalidateProfiles();
  return useMutation<ProfileOut, Error, ProfileIn>({
    mutationFn: (body) => api.createProfile(body),
    onSuccess: invalidate,
  });
}

/** Update an existing search profile. */
export function useUpdateProfile() {
  const invalidate = useInvalidateProfiles();
  return useMutation<ProfileOut, Error, { id: number; body: ProfileIn }>({
    mutationFn: ({ id, body }) => api.updateProfile(id, body),
    onSuccess: invalidate,
  });
}

/** Delete a search profile. */
export function useDeleteProfile() {
  const invalidate = useInvalidateProfiles();
  return useMutation<void, Error, number>({
    mutationFn: (id) => api.deleteProfile(id),
    onSuccess: invalidate,
  });
}
