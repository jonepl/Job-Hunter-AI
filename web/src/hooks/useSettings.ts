import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type SettingsOut, type SettingsUpdate } from "../api/client";

// The global settings + secrets state (ui-spec §14, ADR-031). Not optimistic —
// the server recomputes masked secret status and the differs-from-.env flags, so we
// let the returned state win. Secrets are written through their own mutations.

/** Query key for the global settings state. */
export const settingsQueryKey = ["settings"] as const;

/** Fetch the global settings, `.env` defaults, and masked secret status. */
export function useSettings() {
  return useQuery<SettingsOut>({
    queryKey: settingsQueryKey,
    queryFn: api.getSettings,
  });
}

/** Persist the editable global settings; refresh on success. */
export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation<SettingsOut, Error, SettingsUpdate>({
    mutationFn: (body) => api.updateSettings(body),
    onSuccess: (state) => qc.setQueryData(settingsQueryKey, state),
  });
}

/** Replace a secret (write-only); refresh settings so the masked status updates. */
export function useSetSecret() {
  const qc = useQueryClient();
  return useMutation<unknown, Error, { name: string; value: string }>({
    mutationFn: ({ name, value }) => api.setSecret(name, value),
    onSuccess: () => qc.invalidateQueries({ queryKey: settingsQueryKey }),
  });
}

/** Clear a secret's override, reverting to the `.env` value. */
export function useClearSecret() {
  const qc = useQueryClient();
  return useMutation<unknown, Error, string>({
    mutationFn: (name) => api.clearSecret(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: settingsQueryKey }),
  });
}
