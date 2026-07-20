import { useState } from "react";

import { useJobs } from "../hooks/useJobs";
import { JobCard } from "../components/JobCard";
import { JobDetail } from "../components/JobDetail";
import { JobFilterBar } from "../components/JobFilterBar";
import { DEFAULT_FILTER, filterJobs, type JobFilterId } from "../lib/filters";

// The empty-view copy shown when jobs exist but the active filter matches none —
// distinct from the global "No jobs yet" (ui-spec §6.4).
const FILTERED_EMPTY: Record<JobFilterId, string> = {
  triage: "Nothing left to triage — every job has a decision. Switch to All to review them.",
  pipeline: "No jobs in your pipeline yet. Mark a job applied to track it here.",
  all: "No jobs match this view.",
  saved: "No saved jobs yet. Star a job to keep it here.",
};

// The hub: a scannable list on the left, a detail pane on the right (ui-spec §3).
// Selecting a card drives the pane in place — no routing, matching the design's
// "no new page". On narrow screens the pane becomes a full-width overlay. Every
// list view owns its loading / empty / error states (ui-spec §6.4).

function StateShell({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-card border border-border bg-surface p-8 text-center">
      <h2 className="font-display text-h2">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-small text-text-2">{body}</p>
    </div>
  );
}

// The shell is now full-width (each screen owns its own layout), so the job list
// keeps its centered measure here rather than inheriting it from <main>. The full
// Search layout redesign is a separate plan.
export function JobList() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <JobListBody />
    </div>
  );
}

function JobListBody() {
  const { data, isLoading, isError, refetch } = useJobs();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [filter, setFilter] = useState<JobFilterId>(DEFAULT_FILTER);

  if (isLoading) {
    return (
      <div className="text-small text-text-2" role="status" aria-live="polite">
        Loading jobs…
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-card border border-border bg-surface p-8 text-center">
        <h2 className="font-display text-h2">Couldn’t load your jobs</h2>
        <p className="mx-auto mt-2 max-w-md text-small text-text-2">
          The job service didn’t respond. Check that the API is running, then try again.
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="mt-4 rounded-control border border-border-strong bg-surface px-4 py-2 text-control text-text transition-colors duration-fast hover:border-accent"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <StateShell
        title="No jobs yet"
        body="Run a search to evaluate postings and they’ll show up here, ranked against your threshold."
      />
    );
  }

  const visible = filterJobs(data, filter);

  return (
    <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] lg:gap-6">
      <div data-testid="job-list">
        <JobFilterBar jobs={data} active={filter} onChange={setFilter} />
        {visible.length === 0 ? (
          <div className="rounded-card border border-dashed border-border bg-surface p-8 text-center text-small text-text-2">
            {FILTERED_EMPTY[filter]}
          </div>
        ) : (
          <div className="space-y-4">
            {visible.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                selected={job.id === selectedId}
                onSelect={setSelectedId}
              />
            ))}
          </div>
        )}
      </div>

      {selectedId === null ? (
        <div className="hidden lg:block">
          <div className="rounded-card border border-dashed border-border bg-surface p-8 text-center text-small text-text-2">
            Select a job to see its details.
          </div>
        </div>
      ) : (
        <div className="max-lg:fixed max-lg:inset-0 max-lg:z-40 max-lg:overflow-auto max-lg:bg-bg max-lg:p-6 lg:sticky lg:top-8 lg:max-h-[calc(100vh-4rem)] lg:self-start lg:overflow-y-auto">
          <JobDetail jobId={selectedId} onClose={() => setSelectedId(null)} />
        </div>
      )}
    </div>
  );
}
