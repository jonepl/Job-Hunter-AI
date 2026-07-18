import type { JobSummary } from "../api/client";
import { ProviderBadges } from "./ProviderBadges";
import { ScoreChip } from "./ScoreChip";
import { ThresholdRail } from "./ThresholdRail";

// The reduced W1 card: identity + provider set + score chip + threshold rail.
// Salary, posted-age, work-type, status badge, and the ★ save toggle are not in
// the W1 data model — they arrive with later stories (see plan §1 Context).

export function JobCard({ job }: { job: JobSummary }) {
  return (
    <article className="rounded-card border border-border bg-surface p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="font-display text-body font-semibold">
            {job.url ? (
              <a
                href={job.url}
                target="_blank"
                rel="noreferrer"
                className="text-text transition-colors duration-fast hover:text-accent"
              >
                {job.title}
              </a>
            ) : (
              job.title
            )}
          </h3>
          <p className="mt-1 text-small text-text-2">
            {job.company} · {job.location} ·{" "}
            <ProviderBadges platforms={job.platforms} variant="inline" />
          </p>
        </div>
        <ScoreChip
          score={job.score}
          threshold={job.threshold}
          nearMissFloor={job.nearMissFloor}
        />
      </div>
      <ThresholdRail
        score={job.score}
        threshold={job.threshold}
        nearMissFloor={job.nearMissFloor}
      />
    </article>
  );
}
