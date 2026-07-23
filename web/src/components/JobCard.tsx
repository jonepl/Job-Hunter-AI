import type { JobSummary } from "../api/client";
import { formatPostedAge, formatSalary } from "../lib/salary";
import { ProviderBadges } from "./ProviderBadges";
import { ScoreChip } from "./ScoreChip";
import { StatusPill } from "./StatusPill";
import { ThresholdRail } from "./ThresholdRail";

// The job card (redesign Part E): identity + provider set + score chip + threshold
// rail, with a mono meta line (salary · posting age) and a status pill. The whole
// card is a keyboard-operable button that drives the detail pane. ★ marks a saved
// job in the near-miss colour; a selected card carries an inset accent bar.

interface Props {
  job: JobSummary;
  selected?: boolean;
  onSelect?: (id: number) => void;
}

export function JobCard({ job, selected = false, onSelect }: Props) {
  const showPill = job.status !== "new" && job.status !== "evaluated";
  // Mono meta line: salary and posting age, each omitted when null (Part A.6).
  const metaSegments = [formatSalary(job), formatPostedAge(job.postedAt)].filter(
    (segment): segment is string => segment !== null,
  );

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
      className={`w-full cursor-pointer rounded-card border bg-surface p-4 text-left transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 ${
        selected
          ? "border-accent shadow-[inset_3px_0_0_var(--accent)]"
          : "border-border hover:border-border-strong"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="font-display text-body font-semibold text-text">
            {job.title}
            {job.saved && (
              <span className="ml-1 text-nearmiss" aria-label="Saved">
                ★
              </span>
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

      {(metaSegments.length > 0 || showPill) && (
        <div className="mt-3 flex items-center justify-between gap-3">
          <span className="font-mono text-small text-text-2" data-testid="card-meta">
            {metaSegments.join(" · ")}
          </span>
          {showPill && <StatusPill status={job.status} />}
        </div>
      )}
    </article>
  );
}
