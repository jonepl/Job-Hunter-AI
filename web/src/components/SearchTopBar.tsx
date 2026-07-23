import { useResolvedSelection, useViewedProfile } from "../lib/searchView";
import { RunButton } from "./RunButton";

// The Search screen's top-bar pieces (redesign Part B.3). The center is a "Viewing"
// box reflecting the rail selection (conflict #2 — labelled Viewing, not "Active"),
// with the run control inside it. The right slot gains a threshold indicator showing
// the VIEWED profile's per-profile threshold (ADR-033), rendered only when a profile
// is loaded — never a zero.

export function SearchTopBarCenter() {
  const profile = useViewedProfile();
  const selection = useResolvedSelection();
  const label = profile
    ? profile.name || profile.query
    : selection.kind === "tracked"
      ? "Tracked jobs"
      : "—";

  return (
    <div className="flex max-w-[540px] flex-1 items-center gap-3 rounded-control border border-border-strong bg-bg p-[5px_6px_5px_16px]">
      <div className="min-w-0 flex-1">
        <p className="font-mono text-tick uppercase tracking-[0.08em] text-text-3">Viewing</p>
        <p className="truncate text-control font-semibold text-text">{label}</p>
      </div>
      <RunButton />
    </div>
  );
}

export function SearchThresholdIndicator() {
  const profile = useViewedProfile();
  if (!profile) return null;
  return (
    <span
      className="flex items-center gap-2 text-small font-medium text-text-2"
      data-testid="threshold-indicator"
    >
      <span className="h-2 w-2 rounded-pill bg-qualify" aria-hidden="true" />
      Threshold {profile.scoreThreshold}
    </span>
  );
}
