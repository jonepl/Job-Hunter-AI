import type { JobSummary } from "../api/client";
import { ProviderBadges } from "./ProviderBadges";
import { ScoreChip } from "./ScoreChip";
import { StatusPill } from "./StatusPill";
import { ThresholdRail } from "./ThresholdRail";

// The job card: identity + provider set + score chip + threshold rail. As of W2
// the whole card is a selectable button that drives the detail pane (the title is
// no longer an external link — "View original posting" lives in the pane). A
// status pill shows once a job leaves the machine states; ★ marks a saved job.

interface Props {
  job: JobSummary;
  selected?: boolean;
  onSelect?: (id: number) => void;
}

export function JobCard({ job, selected = false, onSelect }: Props) {
  const showPill = job.status !== "new" && job.status !== "evaluated";

  return (
    <article
      role="button"
      tabIndex={0}
      aria-pressed={selected}
      onClick={() => onSelect?.(job.id)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect?.(job.id);
        }
      }}
      data-testid="job-card"
      data-selected={selected}
      className={`w-full cursor-pointer rounded-card border bg-surface p-5 text-left transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 ${
        selected ? "border-accent" : "border-border hover:border-border-strong"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="font-display text-body font-semibold text-text">
            {job.saved && (
              <span className="mr-1 text-accent" aria-label="Saved">
                ★
              </span>
            )}
            {job.title}
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
      {showPill && (
        <div className="mt-3">
          <StatusPill status={job.status} />
        </div>
      )}
    </article>
  );
}
