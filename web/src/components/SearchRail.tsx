import { useJobs } from "../hooks/useJobs";
import { useProfiles } from "../hooks/useProfiles";
import { useRuns } from "../hooks/useRuns";
import { useResolvedSelection, useSearchView } from "../lib/searchView";
import { isTracked, statusGroup, statusLabel } from "../lib/status";
import { DOT_BG, runDetailLine, runDotColor } from "../lib/runDisplay";
import { relativeTime } from "../lib/time";
import type { JobSummary, ProfileOut, RunOut } from "../api/client";

// The Search screen's left rail (redesign Part C). Three sections — Tracked, Search
// profiles, and a GLOBAL run history (conflict #1: runs are not profile-scoped) —
// separated by hairline rules. Selectable rows share one visual contract with
// <SettingsNav>: an inset accent bar + accent-soft fill when current. Run-history
// rows are static (jobs carry no run_id, so a run can't filter the list — no dead
// click target). React state only; the rail fetches its own data and degrades.

interface Props {
  /** Open the new-profile modal (Part G). */
  onNewProfile: () => void;
}

export function SearchRail({ onNewProfile }: Props) {
  const { data: jobs } = useJobs();
  const { data: profiles } = useProfiles();
  const { data: runs } = useRuns();
  const { select } = useSearchView();
  const resolved = useResolvedSelection();

  const tracked = (jobs ?? []).filter((job) => isTracked(job.status));

  return (
    <nav aria-label="Search navigation" className="text-small">
      <TrackedSection
        jobs={tracked}
        selected={resolved.kind === "tracked"}
        onSelect={() => select({ kind: "tracked" })}
      />
      <Divider />
      <ProfilesSection
        profiles={profiles}
        selectedId={resolved.kind === "profile" ? resolved.id : null}
        onSelect={(id) => select({ kind: "profile", id })}
        onNewProfile={onNewProfile}
      />
      <Divider />
      <RunHistorySection runs={runs} />
    </nav>
  );
}

function Divider() {
  return <hr className="my-[14px] mx-[10px] border-t border-border" />;
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-2 flex items-center justify-between px-[10px] font-mono text-label uppercase tracking-[0.08em] text-text-3">
      {children}
    </h2>
  );
}

/** Shared selectable-row shell (mirrors <SettingsNav>). */
function RailRow({
  selected,
  onSelect,
  label,
  children,
}: {
  selected: boolean;
  onSelect: () => void;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-label={label}
      aria-current={selected ? "page" : undefined}
      className={`flex w-full flex-col gap-1 rounded-control px-3 py-[11px] text-left transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 ${
        selected ? "bg-accent-soft shadow-[inset_2px_0_0_var(--accent)]" : "hover:bg-surface-2"
      }`}
    >
      {children}
    </button>
  );
}

// --- Tracked (C.1) ---------------------------------------------------------

function TrackedSection({
  jobs,
  selected,
  onSelect,
}: {
  jobs: JobSummary[];
  selected: boolean;
  onSelect: () => void;
}) {
  // Per-status counts, in pipeline order; only non-zero chips render (mock line 642).
  const order = ["applied", "started", "interviewing", "offer"] as const;
  const counts = order
    .map((status) => ({ status, n: jobs.filter((j) => j.status === status).length }))
    .filter((c) => c.n > 0);

  return (
    <div>
      <SectionHeader>Tracked</SectionHeader>
      <ul>
        <li>
          <RailRow selected={selected} onSelect={onSelect} label="All in flight">
            <span className="flex items-center justify-between">
              <span className="font-semibold text-text">All in flight</span>
              <span className="font-mono text-label text-text-2">{jobs.length}</span>
            </span>
            {counts.length > 0 && (
              <span className="flex flex-wrap gap-3">
                {counts.map(({ status, n }) => (
                  <span key={status} className="flex items-center gap-1.5 text-caption text-text-3">
                    <span
                      className={`h-[6px] w-[6px] rounded-pill ${DOT_BG[statusGroup(status) === "offer" ? "qualify" : "accent"]}`}
                      aria-hidden="true"
                    />
                    <span className="font-mono">{n}</span> {statusLabel(status)}
                  </span>
                ))}
              </span>
            )}
          </RailRow>
        </li>
      </ul>
    </div>
  );
}

// --- Search profiles (C.2) -------------------------------------------------

function ProfilesSection({
  profiles,
  selectedId,
  onSelect,
  onNewProfile,
}: {
  profiles: ProfileOut[] | undefined;
  selectedId: number | null;
  onSelect: (id: number) => void;
  onNewProfile: () => void;
}) {
  return (
    <div>
      <SectionHeader>
        Search profiles
        <button
          type="button"
          onClick={onNewProfile}
          className="font-mono text-label text-accent transition-colors duration-fast hover:text-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          + New
        </button>
      </SectionHeader>
      {!profiles || profiles.length === 0 ? (
        <p className="px-3 text-caption text-text-3">No profiles yet.</p>
      ) : (
        <ul className="space-y-1">
          {profiles.map((profile) => (
            <li key={profile.id}>
              <RailRow
                selected={profile.id === selectedId}
                onSelect={() => onSelect(profile.id)}
                label={profile.name || profile.query}
              >
                <span className="flex items-center justify-between gap-2">
                  <span className="truncate font-semibold text-text">
                    {profile.name || profile.query}
                  </span>
                  {profile.id === selectedId && (
                    <span className="shrink-0 rounded-pill bg-accent-soft px-2 font-mono text-tick uppercase tracking-[0.08em] text-accent">
                      Active
                    </span>
                  )}
                </span>
                <span className="flex items-center gap-1.5 font-mono text-caption text-text-3">
                  <span className="h-[6px] w-[6px] rounded-pill bg-text-3" aria-hidden="true" />
                  {profile.location} · threshold {profile.scoreThreshold}
                </span>
              </RailRow>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// --- Run history (C.3) — global, static rows -------------------------------

function RunHistorySection({ runs }: { runs: RunOut[] | undefined }) {
  return (
    <div>
      <SectionHeader>Run history</SectionHeader>
      {!runs || runs.length === 0 ? (
        <p className="px-3 text-caption text-text-3">No runs yet.</p>
      ) : (
        <ul className="space-y-1" data-testid="run-history">
          {runs.map((run, i) => (
            <li key={run.id} className="flex flex-col gap-1 rounded-control px-3 py-[9px]">
              <span className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2 text-text-2">
                  <span
                    className={`h-2 w-2 rounded-pill ${DOT_BG[runDotColor(run)]}`}
                    aria-hidden="true"
                  />
                  {relativeTime(run.startedAt) ?? "just now"}
                </span>
                {i === 0 && (
                  <span className="shrink-0 font-mono text-tick uppercase tracking-[0.08em] text-text-3">
                    Latest
                  </span>
                )}
              </span>
              <span className="pl-4 font-mono text-caption text-text-3">
                {runDetailLine(run)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
