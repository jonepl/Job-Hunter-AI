import type { JobSummary } from "../api/client";
import { JOB_FILTERS, countFor, type JobFilterId } from "../lib/filters";

// The status-view chip row (W3). One chip per filter with a live count, the active
// chip filled; a mono "N active · M total" line so nothing feels hidden; and a clear
// ✕ on any non-"all" active filter so the view is always visibly clearable and All is
// one tap away. Pure/presentational — selection is React state in the parent, never
// browser storage (design.md).

interface Props {
  jobs: JobSummary[];
  active: JobFilterId;
  onChange: (id: JobFilterId) => void;
}

export function JobFilterBar({ jobs, active, onChange }: Props) {
  const activeCount = countFor(jobs, active);
  const total = jobs.length;

  return (
    <div className="mb-4 space-y-2" data-testid="job-filter-bar">
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filter jobs">
        {JOB_FILTERS.map((filter) => {
          const isActive = filter.id === active;
          const count = countFor(jobs, filter.id);
          return (
            <button
              key={filter.id}
              type="button"
              aria-pressed={isActive}
              onClick={() => onChange(filter.id)}
              className={`inline-flex items-center gap-2 rounded-pill px-3 py-1 text-small transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 ${
                isActive
                  ? "bg-accent-soft text-accent"
                  : "bg-surface-2 text-text-2 hover:text-text"
              }`}
            >
              {filter.label}
              <span className="font-mono">{count}</span>
              {isActive && filter.id !== "all" && (
                <span
                  role="button"
                  tabIndex={0}
                  aria-label="Clear filter"
                  onClick={(event) => {
                    event.stopPropagation();
                    onChange("all");
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      event.stopPropagation();
                      onChange("all");
                    }
                  }}
                  className="cursor-pointer rounded-pill px-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                >
                  ✕
                </span>
              )}
            </button>
          );
        })}
      </div>
      <p className="text-caption text-text-3">
        <span className="font-mono text-text-2">{activeCount}</span> active ·{" "}
        <span className="font-mono text-text-2">{total}</span> total
      </p>
    </div>
  );
}
