import { useCallback } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";

import { useProfiles } from "../hooks/useProfiles";
import type { ProfileOut } from "../api/client";

// The Search screen's rail selection, shared between the top bar (which shows the
// "Viewing" box + threshold indicator) and the results column (rail + header +
// list). The selection lives in the URL search params so it survives a reload and
// is deep-linkable (see router.tsx). Two mutually exclusive view modes:
//   - a specific search profile (the "Latest run" view)  -> ?profile=<id>
//   - the global Tracked view (all in-flight jobs)        -> ?view=tracked
// Neither param present -> resolve to the first profile (or Tracked when none).

export type SearchSelection =
  | { kind: "tracked" }
  | { kind: "profile"; id: number };

/** The URL search params that encode the rail selection. */
export interface SearchParams {
  view?: "tracked";
  profile?: number;
}

interface SearchViewValue {
  /** The raw selection; null means "not yet chosen — resolve to the first profile". */
  selection: SearchSelection | null;
  select: (selection: SearchSelection) => void;
}

/** Read/write the rail selection through the URL search params. */
export function useSearchView(): SearchViewValue {
  const search = useSearch({ strict: false }) as SearchParams;
  const navigate = useNavigate();

  const selection: SearchSelection | null =
    search.view === "tracked"
      ? { kind: "tracked" }
      : typeof search.profile === "number"
        ? { kind: "profile", id: search.profile }
        : null;

  const select = useCallback(
    (next: SearchSelection) => {
      // The two modes are mutually exclusive, so each write replaces the search
      // wholesale — never both params at once.
      const params: SearchParams =
        next.kind === "tracked" ? { view: "tracked" } : { profile: next.id };
      void navigate({ to: "/", search: params });
    },
    [navigate],
  );

  return { selection, select };
}

/**
 * The effective selection, resolving the initial null to the first profile (or
 * Tracked when no profiles exist yet). Everything that renders from the selection
 * reads this so the default landing view matches the design without a stored choice.
 */
export function useResolvedSelection(): SearchSelection {
  const { selection } = useSearchView();
  const { data: profiles } = useProfiles();
  if (selection) {
    // Guard a stale/deleted profile id in the URL — fall back to the default.
    if (selection.kind === "profile" && profiles && !profiles.some((p) => p.id === selection.id)) {
      return profiles.length > 0 ? { kind: "profile", id: profiles[0].id } : { kind: "tracked" };
    }
    return selection;
  }
  if (profiles && profiles.length > 0) return { kind: "profile", id: profiles[0].id };
  return { kind: "tracked" };
}

/** The viewed profile for the current selection, or null in the Tracked view. */
export function useViewedProfile(): ProfileOut | null {
  const resolved = useResolvedSelection();
  const { data: profiles } = useProfiles();
  if (resolved.kind !== "profile" || !profiles) return null;
  return profiles.find((p) => p.id === resolved.id) ?? null;
}
