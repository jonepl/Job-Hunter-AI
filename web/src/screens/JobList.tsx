import { useState } from "react";

import { useJobs } from "../hooks/useJobs";
import { JobCard } from "../components/JobCard";
import { JobDetail } from "../components/JobDetail";

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

export function JobList() {
  const { data, isLoading, isError, refetch } = useJobs();
  const [selectedId, setSelectedId] = useState<number | null>(null);

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

  return (
    <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] lg:gap-6">
      <div className="space-y-4" data-testid="job-list">
        {data.map((job) => (
          <JobCard
            key={job.id}
            job={job}
            selected={job.id === selectedId}
            onSelect={setSelectedId}
          />
        ))}
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
