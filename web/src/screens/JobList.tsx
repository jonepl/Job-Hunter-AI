import { useJobs } from "../hooks/useJobs";
import { JobCard } from "../components/JobCard";

// The W1 hub: a single scannable column of persisted jobs. Every list view owns
// its loading / empty / error states as first-class screens (ui-spec §6.4), not
// afterthoughts. The three-column IA (rail, detail pane) arrives in W2/W3.

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
    <div className="space-y-4" data-testid="job-list">
      {data.map((job) => (
        <JobCard key={job.id} job={job} />
      ))}
    </div>
  );
}
