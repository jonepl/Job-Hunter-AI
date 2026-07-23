import type { JobSummary, RunOut } from "../../api/client";
import { scoreState } from "../../lib/score";
import { JobCard } from "../JobCard";

// Zero-results report (redesign Part F.3): the latest run succeeded but nothing
// qualified. States how many were evaluated, then lists the top near-misses.
//
// The mock's "Lowering to 70 would have delivered 3" panel needs a suggested
// threshold the API does not return — RunReport.suggested_threshold is backend-owned
// (output-and-scheduling.md) and must never be recomputed in the browser. So the
// panel is only rendered when a suggestion is supplied; today none is, and it is
// correctly absent rather than faked.

interface Props {
  run: RunOut;
  jobs: JobSummary[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  /** Backend-owned suggested threshold; undefined today (never computed client-side). */
  suggestedThreshold?: number | null;
}

export function ZeroResults({ run, jobs, selectedId, onSelect, suggestedThreshold }: Props) {
  const nearMisses = jobs
    .filter((job) => scoreState(job.score, job.threshold, job.nearMissFloor) === "nearmiss")
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .slice(0, 5);

  return (
    <div data-testid="zero-results">
      <div className="rounded-card border border-border bg-surface p-6 text-center">
        <h2 className="font-display text-h3 text-nearmiss">No qualifying matches</h2>
        <p className="mx-auto mt-2 max-w-md text-small text-text-2">
          Evaluated <span className="font-mono">{run.jobsFound}</span>{" "}
          {run.jobsFound === 1 ? "job" : "jobs"} — none reached the threshold.
        </p>
        {suggestedThreshold != null && (
          <p className="mx-auto mt-3 max-w-md rounded-control bg-nearmiss-soft px-3 py-2 text-small text-nearmiss">
            Lowering to <span className="font-mono">{suggestedThreshold}</span> would have
            surfaced near-misses.
          </p>
        )}
      </div>

      {nearMisses.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 font-mono text-label uppercase tracking-[0.08em] text-text-3">
            Top near-misses
          </p>
          <div className="space-y-4">
            {nearMisses.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                selected={job.id === selectedId}
                onSelect={onSelect}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
