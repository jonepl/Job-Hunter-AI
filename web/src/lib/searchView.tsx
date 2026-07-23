import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import { useProfiles } from "../hooks/useProfiles";
import type { ProfileOut } from "../api/client";

// The Search screen's rail selection, shared between the top bar (which shows the
// "Viewing" box + threshold indicator) and the results column (rail + header +
// list). React state only — no browser storage (design.md). Two view modes:
//   - a specific search profile (the "Latest run" view), or
//   - the global Tracked view (all in-flight jobs across profiles).

export type SearchSelection =
  | { kind: "tracked" }
  | { kind: "profile"; id: number };

interface SearchViewValue {
  /** The raw selection; null means "not yet chosen — resolve to the first profile". */
  selection: SearchSelection | null;
  select: (selection: SearchSelection) => void;
}

const SearchViewContext = createContext<SearchViewValue | null>(null);

/** Provide the rail selection to the whole Search subtree (top bar + results). */
export function SearchViewProvider({ children }: { children: ReactNode }) {
  const [selection, setSelection] = useState<SearchSelection | null>(null);
  const value = useMemo(
    () => ({ selection, select: setSelection }),
    [selection],
  );
  return <SearchViewContext.Provider value={value}>{children}</SearchViewContext.Provider>;
}

/** Read/write the raw rail selection. Throws outside a provider. */
export function useSearchView(): SearchViewValue {
  const ctx = useContext(SearchViewContext);
  if (!ctx) {
    throw new Error("useSearchView must be used within a SearchViewProvider");
  }
  return ctx;
}

/**
 * The effective selection, resolving the initial null to the first profile (or
 * Tracked when no profiles exist yet). Everything that renders from the selection
 * reads this so the default landing view matches the design without a stored choice.
 */
export function useResolvedSelection(): SearchSelection {
  const { selection } = useSearchView();
  const { data: profiles } = useProfiles();
  if (selection) return selection;
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
