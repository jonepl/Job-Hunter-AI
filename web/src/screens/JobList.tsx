import { useState } from "react";

import { useJobs } from "../hooks/useJobs";
import { useRuns } from "../hooks/useRuns";
import { ConfigureProfileModal } from "../components/ConfigureProfileModal";
import { JobCard } from "../components/JobCard";
import { JobDetail } from "../components/JobDetail";
import { JobFilterBar } from "../components/JobFilterBar";
import { NewProfileModal } from "../components/NewProfileModal";
import { SearchRail } from "../components/SearchRail";
import { FilteredEmpty } from "../components/searchStates/FilteredEmpty";
import { RunFailed } from "../components/searchStates/RunFailed";
import { RunningBanner } from "../components/searchStates/RunningBanner";
import { ZeroResults } from "../components/searchStates/ZeroResults";
import { EMPTY_FILTER, applyFilters, type FilterState } from "../lib/filters";
import { useResolvedSelection } from "../lib/searchView";
import { isTracked, statusLabel } from "../lib/status";
import { relativeTime } from "../lib/time";
import type { JobSummary, ProfileOut, RunOut } from "../api/client";

// The Search screen shell (redesign Part B): a 284px navigation rail, a 484px
// results column, and a fluid detail pane, each scrolling independently under the
// 66px TopBar. The rail collapses to a drawer below xl and the whole thing to a
// single column below lg. Rail selection is shared React state (searchView.tsx).

export function JobList() {
  const { data: jobs, isLoading, isError, refetch } = useJobs();
  const { data: runs } = useRuns();
  const selection = useResolvedSelection();

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [filter, setFilter] = useState<FilterState>(EMPTY_FILTER);
  const [railOpen, setRailOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  // Multi-select for batch runs lives here (not in <SearchRail>) so the desktop rail and
  // the mobile drawer share one selection; the ⚙ target lives here so the modal renders
  // at the screen shell (search v2 §C/§F). React state only — no browser storage.
  const [selectedProfileIds, setSelectedProfileIds] = useState<Set<number>>(new Set());
  const [configureProfile, setConfigureProfile] = useState<ProfileOut | null>(null);

  const allJobs = jobs ?? [];
  // Base list per view: Tracked shows in-flight jobs; a profile view (the "Latest
  // run") shows the full evaluated list — jobs aren't profile-tagged (conflict #1).
  const base =
    selection.kind === "tracked" ? allJobs.filter((j) => isTracked(j.status)) : allJobs;
  const visible = applyFilters(base, filter);
  const latestRun = runs?.[0];

  // The detail pane defaults to the first result when nothing has been explicitly
  // picked, so the pane is never an empty placeholder while jobs exist. `selectedId`
  // stays the *explicit* choice (it drives the <lg overlay, which must only open on a
  // real tap); `displayedId` is what the lg+ column actually renders.
  const displayedId = selectedId ?? visible[0]?.id ?? null;

  return (
    <div className="flex h-[calc(100vh-66px)]">
      <aside className="hidden w-[284px] shrink-0 overflow-y-auto border-r border-border bg-surface p-5 px-[14px] as-scroll xl:block">
        <SearchRail
          onNewProfile={() => setModalOpen(true)}
          onConfigure={setConfigureProfile}
          selectedIds={selectedProfileIds}
          onSelectionChange={setSelectedProfileIds}
        />
      </aside>

      {railOpen && (
        <RailDrawer onClose={() => setRailOpen(false)}>
          <SearchRail
            onNewProfile={() => {
              setRailOpen(false);
              setModalOpen(true);
            }}
            onConfigure={(profile) => {
              setRailOpen(false);
              setConfigureProfile(profile);
            }}
            selectedIds={selectedProfileIds}
            onSelectionChange={setSelectedProfileIds}
          />
        </RailDrawer>
      )}

      <section className="flex w-full flex-col border-r border-border lg:w-[484px] lg:shrink-0">
        <ResultsHeader
          selection={selection}
          latestRun={latestRun}
          visibleCount={visible.length}
          baseCount={base.length}
          base={base}
          onOpenRail={() => setRailOpen(true)}
        />
        <div className="flex-1 overflow-y-auto px-5 py-4 as-scroll">
          <JobFilterBar jobs={base} filter={filter} onChange={setFilter} />
          <div className="mt-4">
            <ResultsBody
              isLoading={isLoading}
              isError={isError}
              onRetry={refetch}
              selection={selection}
              latestRun={latestRun}
              base={base}
              visible={visible}
              allJobs={allJobs}
              onClearFilter={() => setFilter(EMPTY_FILTER)}
              selectedId={displayedId}
              onSelect={setSelectedId}
            />
          </div>
        </div>
      </section>

      {/* Detail pane: an in-flow column on lg+, a full-screen overlay on <lg when a
          job is selected, hidden on <lg otherwise. One <JobDetail>, never two. */}
      <section
        className={`min-w-0 flex-1 overflow-y-auto bg-bg px-9 py-[30px] as-scroll lg:block ${
          selectedId === null
            ? "hidden lg:block"
            : "max-lg:fixed max-lg:inset-0 max-lg:z-40 max-lg:p-6"
        }`}
      >
        {displayedId === null ? (
          <div className="rounded-card border border-dashed border-border bg-surface p-8 text-center text-small text-text-2">
            No job to show yet.
          </div>
        ) : (
          <JobDetail jobId={displayedId} onClose={() => setSelectedId(null)} />
        )}
      </section>

      {modalOpen && <NewProfileModal onClose={() => setModalOpen(false)} />}
      {configureProfile && (
        <ConfigureProfileModal
          profile={configureProfile}
          onClose={() => setConfigureProfile(null)}
        />
      )}
    </div>
  );
}

/** The off-canvas rail drawer for < xl viewports. */
function RailDrawer({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40 flex xl:hidden" role="dialog" aria-label="Profiles">
      <div className="flex-1 bg-text/40" onClick={onClose} />
      <aside className="ml-auto w-[284px] overflow-y-auto border-l border-border bg-surface p-5 px-[14px] as-scroll">
        {children}
      </aside>
    </div>
  );
}

function ResultsHeader({
  selection,
  latestRun,
  visibleCount,
  baseCount,
  base,
  onOpenRail,
}: {
  selection: ReturnType<typeof useResolvedSelection>;
  latestRun: RunOut | undefined;
  visibleCount: number;
  baseCount: number;
  base: JobSummary[];
  onOpenRail: () => void;
}) {
  const tracked = selection.kind === "tracked";
  const title = tracked ? "Tracked jobs" : "Latest run";
  const timestamp = tracked
    ? "across all runs"
    : latestRun
      ? (relativeTime(latestRun.startedAt) ?? "—")
      : "—";
  const subline = tracked ? trackedBreakdown(base) : `Showing ${visibleCount} of ${baseCount} matches`;

  return (
    <div className="border-b border-border px-5 py-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onOpenRail}
            className="rounded-control border border-border-strong px-2.5 py-1 text-caption text-text-2 transition-colors duration-fast hover:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 xl:hidden"
          >
            Profiles
          </button>
          <h2 className="font-display text-h3 font-semibold">{title}</h2>
        </div>
        <span className="font-mono text-caption text-text-3">{timestamp}</span>
      </div>
      <p className="mt-1 text-caption text-text-3">{subline || "Nothing in flight"}</p>
    </div>
  );
}

/** The Tracked view's " · "-joined status breakdown, e.g. "3 applied · 2 interviewing". */
function trackedBreakdown(jobs: JobSummary[]): string {
  const order = ["applied", "started", "interviewing", "offer"] as const;
  return order
    .map((status) => ({ status, n: jobs.filter((j) => j.status === status).length }))
    .filter((c) => c.n > 0)
    .map((c) => `${c.n} ${statusLabel(c.status).toLowerCase()}`)
    .join(" · ");
}

function ResultsBody({
  isLoading,
  isError,
  onRetry,
  selection,
  latestRun,
  base,
  visible,
  allJobs,
  onClearFilter,
  selectedId,
  onSelect,
}: {
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  selection: ReturnType<typeof useResolvedSelection>;
  latestRun: RunOut | undefined;
  base: JobSummary[];
  visible: JobSummary[];
  allJobs: JobSummary[];
  onClearFilter: () => void;
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  if (isLoading) {
    return (
      <p className="text-small text-text-2" role="status" aria-live="polite">
        Loading jobs…
      </p>
    );
  }

  if (isError) {
    return (
      <div className="rounded-card border border-border bg-surface p-8 text-center">
        <h2 className="font-display text-h3">Couldn’t load your jobs</h2>
        <p className="mx-auto mt-2 max-w-md text-small text-text-2">
          The job service didn’t respond. Check that the API is running, then try again.
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-control border border-border-strong bg-surface px-4 py-2 text-control text-text transition-colors duration-fast hover:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          Try again
        </button>
      </div>
    );
  }

  const isProfileView = selection.kind === "profile";
  const running = latestRun?.status === "running";

  // Run-state panels apply only to the profile ("Latest run") view (Part F).
  if (isProfileView && latestRun?.status === "failed") {
    return <RunFailed run={latestRun} />;
  }
  if (isProfileView && latestRun?.status === "succeeded" && latestRun.qualifying === 0) {
    return (
      <ZeroResults
        run={latestRun}
        jobs={allJobs}
        selectedId={selectedId}
        onSelect={onSelect}
      />
    );
  }

  if (base.length === 0) {
    return (
      <>
        {isProfileView && running && <RunningBanner />}
        <div className="rounded-card border border-border bg-surface p-8 text-center">
          <h2 className="font-display text-h3">
            {selection.kind === "tracked" ? "Nothing in flight yet" : "No jobs yet"}
          </h2>
          <p className="mx-auto mt-2 max-w-md text-small text-text-2">
            {selection.kind === "tracked"
              ? "Mark a job applied to start tracking it here."
              : "Run a search to evaluate postings and they’ll show up here, ranked against your threshold."}
          </p>
        </div>
      </>
    );
  }

  return (
    <>
      {isProfileView && running && <RunningBanner />}
      {visible.length === 0 ? (
        <FilteredEmpty baseCount={base.length} onClear={onClearFilter} />
      ) : (
        <div className="space-y-4" data-testid="job-list">
          {visible.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              selected={job.id === selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </>
  );
}
