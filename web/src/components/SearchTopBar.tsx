import { useProfiles } from "../hooks/useProfiles";
import { useRuns } from "../hooks/useRuns";
import { useViewedProfile } from "../lib/searchView";
import { describeNextRun } from "../lib/time";

// The Search screen's top-bar pieces (v2 §D). Per the v2 design the center is *only* the
// live run strip — the v1 "Viewing" box + global run button are gone (running now happens
// through the rail's per-profile "Run now" / "Run N selected" and the empty state). The
// right slot keeps the threshold indicator showing the VIEWED profile's per-profile
// threshold (ADR-033), rendered only when a profile is loaded — never a zero.

export function SearchTopBarCenter() {
  return (
    <div className="flex flex-1 items-center gap-4">
      <SearchRunStrip />
    </div>
  );
}

// The next scheduled fire across all enabled + scheduled profiles, or null when none is
// scheduled (the strip then shows nothing — the graceful degradation of conflict #4).
function soonestNextRun(nextRuns: (string | null)[]): string | null {
  const times = nextRuns
    .filter((iso): iso is string => iso !== null)
    .map((iso) => ({ iso, t: new Date(iso).getTime() }))
    .filter((x) => !Number.isNaN(x.t))
    .sort((a, b) => a.t - b.t);
  return times[0]?.iso ?? null;
}

/**
 * The top-bar run strip (v2 §D): "Running N profile(s)…" while a run is live, else
 * "Next scheduled run <when>" from the soonest per-profile next-run time. Renders
 * nothing when neither applies (no active run and nothing scheduled) — a safe degrade.
 */
export function SearchRunStrip() {
  const { data: runs } = useRuns();
  const { data: profiles } = useProfiles();

  const active = runs?.find((r) => r.status === "running");
  if (active) {
    // A per-profile run targets one; a global batch runs every enabled profile.
    const n =
      active.profileId != null ? 1 : (profiles?.filter((p) => p.enabled).length ?? 0);
    return (
      <span
        className="flex items-center gap-2 text-small text-text-2"
        role="status"
        aria-live="polite"
        data-testid="run-strip"
      >
        <span className="h-2 w-2 animate-pulse rounded-pill bg-accent" aria-hidden="true" />
        Running {n} profile{n === 1 ? "" : "s"}…
      </span>
    );
  }

  const next = soonestNextRun((profiles ?? []).map((p) => p.nextRunAt));
  const when = describeNextRun(next);
  if (!when) return null;
  return (
    <span className="flex items-center gap-2 text-small text-text-3" data-testid="run-strip">
      <span className="h-2 w-2 rounded-pill bg-text-3" aria-hidden="true" />
      Next scheduled run {when}
    </span>
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
