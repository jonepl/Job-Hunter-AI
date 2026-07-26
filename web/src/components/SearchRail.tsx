import { useEffect, useRef } from "react";

import { useJobs } from "../hooks/useJobs";
import { useProfiles } from "../hooks/useProfiles";
import { useRunProfilesSequentially, useRuns } from "../hooks/useRuns";
import { useResolvedSelection, useSearchView } from "../lib/searchView";
import { isTracked, statusGroup, statusLabel } from "../lib/status";
import {
  DOT_BG,
  PROFILE_DOT_BG,
  profileStatusLine,
  runDetailLine,
  runDotColor,
  runSourceLabel,
} from "../lib/runDisplay";
import { relativeTime } from "../lib/time";
import type { JobSummary, ProfileOut, RunOut } from "../api/client";

// The Search screen's left rail (redesign Part C, v2). Three sections — Tracked, Search
// profiles, and a per-profile Run history — separated by hairline rules. v2 turns the
// profiles section interactive: a checkbox + ⚙ gear per row, a Select-all toggle, a live
// per-profile status line, and a sticky "Run N selected now" button that fires the
// selected profiles **sequentially** (the server's single-flight guard serializes them).
// The run history is now scoped to the selected profile and tags each run Ad-hoc /
// Scheduled. React state only; the rail fetches its own data and degrades.

interface Props {
  /** Open the new-profile modal. */
  onNewProfile: () => void;
  /** Open the configure-profile modal for a profile (the ⚙ gear). */
  onConfigure: (profile: ProfileOut) => void;
  /** The multi-select set (held in JobList so both rail instances share it). */
  selectedIds: Set<number>;
  /** Replace the multi-select set. */
  onSelectionChange: (next: Set<number>) => void;
}

export function SearchRail({ onNewProfile, onConfigure, selectedIds, onSelectionChange }: Props) {
  const { data: jobs } = useJobs();
  const { data: profiles } = useProfiles();
  const { data: runs } = useRuns();
  const { select } = useSearchView();
  const resolved = useResolvedSelection();

  const tracked = (jobs ?? []).filter((job) => isTracked(job.status));
  const viewedProfileId = resolved.kind === "profile" ? resolved.id : null;
  const viewedProfile = profiles?.find((p) => p.id === viewedProfileId) ?? null;

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
        runs={runs}
        selectedId={viewedProfileId}
        onSelect={(id) => select({ kind: "profile", id })}
        onNewProfile={onNewProfile}
        onConfigure={onConfigure}
        selectedIds={selectedIds}
        onSelectionChange={onSelectionChange}
      />
      <Divider />
      <RunHistorySection profile={viewedProfile} />
    </nav>
  );
}

function Divider() {
  return <hr className="my-[14px] mx-[10px] border-t border-border" />;
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-2 flex items-center justify-between gap-2 px-[10px] font-mono text-label uppercase tracking-[0.08em] text-text-3">
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
  runs,
  selectedId,
  onSelect,
  onNewProfile,
  onConfigure,
  selectedIds,
  onSelectionChange,
}: {
  profiles: ProfileOut[] | undefined;
  runs: RunOut[] | undefined;
  selectedId: number | null;
  onSelect: (id: number) => void;
  onNewProfile: () => void;
  onConfigure: (profile: ProfileOut) => void;
  selectedIds: Set<number>;
  onSelectionChange: (next: Set<number>) => void;
}) {
  const batch = useRunProfilesSequentially();

  // Clear the multi-select once a batch finishes cleanly (running true → false, no error).
  const wasRunning = useRef(false);
  useEffect(() => {
    if (wasRunning.current && !batch.running && batch.error === null) {
      onSelectionChange(new Set());
    }
    wasRunning.current = batch.running;
  }, [batch.running, batch.error, onSelectionChange]);

  const list = profiles ?? [];
  const allSelected = list.length > 0 && list.every((p) => selectedIds.has(p.id));

  function toggleOne(id: number) {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onSelectionChange(next);
  }

  function toggleAll() {
    onSelectionChange(allSelected ? new Set() : new Set(list.map((p) => p.id)));
  }

  /** The most recent per-profile run (global list is newest-first; batches lack an id). */
  const latestRunFor = (id: number) => runs?.find((r) => r.profileId === id);

  return (
    <div>
      <SectionHeader>
        Search profiles
        <span className="flex items-center gap-3">
          {list.length > 0 && (
            <button
              type="button"
              onClick={toggleAll}
              className="font-mono text-label text-text-3 transition-colors duration-fast hover:text-text-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
            >
              {allSelected ? "Clear" : "Select all"}
            </button>
          )}
          <button
            type="button"
            onClick={onNewProfile}
            className="font-mono text-label text-accent transition-colors duration-fast hover:text-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
          >
            + New
          </button>
        </span>
      </SectionHeader>

      {list.length === 0 ? (
        <p className="px-3 text-caption text-text-3">No profiles yet.</p>
      ) : (
        <>
          <ul className="space-y-1">
            {list.map((profile) => (
              <li key={profile.id}>
                <ProfileRow
                  profile={profile}
                  latestRun={latestRunFor(profile.id)}
                  active={profile.id === selectedId}
                  checked={selectedIds.has(profile.id)}
                  onSelect={() => onSelect(profile.id)}
                  onToggle={() => toggleOne(profile.id)}
                  onConfigure={() => onConfigure(profile)}
                />
              </li>
            ))}
          </ul>
          <RunSelectedButton batch={batch} selectedIds={selectedIds} />
        </>
      )}
    </div>
  );
}

function ProfileRow({
  profile,
  latestRun,
  active,
  checked,
  onSelect,
  onToggle,
  onConfigure,
}: {
  profile: ProfileOut;
  latestRun: RunOut | undefined;
  active: boolean;
  checked: boolean;
  onSelect: () => void;
  onToggle: () => void;
  onConfigure: () => void;
}) {
  const name = profile.name || profile.query;
  const status = profileStatusLine(profile, latestRun);

  // The whole row is one selectable surface (hover/active styling lives here), with the
  // checkbox and ⚙ gear nested *inside* it. HTML forbids nesting interactive controls in
  // a <button>, so the middle text region is the button and the container is a plain div.
  return (
    <div
      className={`flex items-center gap-2 rounded-control pl-3 pr-1.5 transition-colors duration-fast ${
        active ? "bg-accent-soft shadow-[inset_2px_0_0_var(--accent)]" : "hover:bg-surface-2"
      }`}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={onToggle}
        aria-label={`Select ${name}`}
        className="h-[18px] w-[18px] shrink-0 accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
      />
      <button
        type="button"
        onClick={onSelect}
        aria-label={name}
        aria-current={active ? "page" : undefined}
        className="flex min-w-0 flex-1 flex-col gap-1 rounded-control py-[11px] text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
      >
        <span className="flex min-w-0 items-center justify-between gap-2">
          <span className="min-w-0 flex-1 truncate font-semibold text-text">{name}</span>
          {active && (
            <span className="shrink-0 rounded-pill bg-accent-soft px-2 font-mono text-tick uppercase tracking-[0.08em] text-accent">
              Active
            </span>
          )}
        </span>
        <span className="flex min-w-0 items-center gap-1.5 font-mono text-caption text-text-3">
          <span
            className={`h-[6px] w-[6px] shrink-0 rounded-pill ${PROFILE_DOT_BG[status.dot]}`}
            aria-hidden="true"
          />
          <span className="min-w-0 flex-1 truncate">{status.text}</span>
        </span>
      </button>
      <button
        type="button"
        onClick={onConfigure}
        aria-label={`Configure ${name}`}
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-body leading-none text-text-3 transition-colors duration-fast hover:bg-surface-2 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
      >
        <span aria-hidden="true">⚙</span>
      </button>
    </div>
  );
}

function RunSelectedButton({
  batch,
  selectedIds,
}: {
  batch: ReturnType<typeof useRunProfilesSequentially>;
  selectedIds: Set<number>;
}) {
  const count = selectedIds.size;
  const label = batch.running
    ? `Running ${Math.min(batch.current + 1, batch.total)} of ${batch.total}…`
    : `Run ${count} selected now`;

  return (
    <div className="sticky bottom-0 mt-3 space-y-2 bg-surface pt-2">
      {batch.error && (
        <p className="px-1 text-caption text-danger" role="alert">
          Batch halted — {batch.error}
        </p>
      )}
      <button
        type="button"
        onClick={() => batch.start([...selectedIds])}
        disabled={count === 0 || batch.running}
        className="w-full rounded-control bg-accent px-3 py-2 text-control font-semibold text-accent-on transition-colors duration-fast hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-50"
      >
        {label}
      </button>
    </div>
  );
}

// --- Run history (C.3) — scoped to the selected profile --------------------

function RunHistorySection({ profile }: { profile: ProfileOut | null }) {
  // Scoped to the viewed profile; global "run all" batches are excluded server-side.
  const { data: runs } = useRuns(profile?.id);
  const caption = profile ? profile.name || profile.query : "a profile";

  return (
    <div>
      <SectionHeader>Run history</SectionHeader>
      <p className="mb-2 px-3 text-caption text-text-3">For {caption}</p>
      {!profile ? (
        <p className="px-3 text-caption text-text-3">Select a profile to see its runs.</p>
      ) : !runs || runs.length === 0 ? (
        <p className="px-3 text-caption text-text-3">No runs yet for this profile.</p>
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
                <span className="shrink-0 rounded-pill bg-surface-2 px-2 font-mono text-tick uppercase tracking-[0.08em] text-text-3">
                  {runSourceLabel(run)}
                </span>
              </span>
              <span className="pl-4 font-mono text-caption text-text-3">{runDetailLine(run)}</span>
              {i === 0 && (
                <span className="pl-4 font-mono text-tick uppercase tracking-[0.08em] text-text-3">
                  Latest
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
