import type { HumanStatus, JobSummary } from "../api/client";
import {
  EMPTY_FILTER,
  LABEL_CHIPS,
  isFilterActive,
  labelCount,
  qualifyingCount,
  savedCount,
  toggleLabel,
  type FilterState,
} from "../lib/filters";

// The Search filter bar (redesign Part D.2): multi-select status chips OR-ed
// together, a Saved bookmark chip, then — after a divider — an independent
// "Qualifying only" score toggle and a Clear. Counts are drawn from the UNFILTERED
// base list so a chip never reads 0 while its rows show. Pure/presentational —
// state lives in the parent (design.md, no browser storage).

interface Props {
  /** The unfiltered base list — the source of every chip count. */
  jobs: JobSummary[];
  filter: FilterState;
  onChange: (filter: FilterState) => void;
}

/** Status-dot colour per chip (accent for in-flight, gray for "not interested"). */
const STATUS_DOT: Record<HumanStatus, string> = {
  applied: "bg-accent",
  started: "bg-accent",
  interviewing: "bg-accent",
  offer: "bg-qualify",
  rejected: "bg-danger",
  not_interested: "bg-below",
};

export function JobFilterBar({ jobs, filter, onChange }: Props) {
  const active = isFilterActive(filter);

  return (
    <div
      className="flex flex-wrap items-center gap-2"
      role="group"
      aria-label="Filter jobs"
      data-testid="job-filter-bar"
    >
      {LABEL_CHIPS.map(({ status, label }) => (
        <Chip
          key={status}
          label={label}
          count={labelCount(jobs, status)}
          dot={STATUS_DOT[status]}
          active={filter.labels.includes(status)}
          palette="accent"
          onClick={() => onChange(toggleLabel(filter, status))}
        />
      ))}

      <Chip
        label="Saved"
        count={savedCount(jobs)}
        dot="bg-nearmiss"
        active={filter.saved}
        palette="accent"
        onClick={() => onChange({ ...filter, saved: !filter.saved })}
      />

      <span className="mx-1 h-5 w-px bg-border" aria-hidden="true" />

      <Chip
        label="Qualifying only"
        count={qualifyingCount(jobs)}
        dot="bg-qualify"
        active={filter.qualifyingOnly}
        palette="qualify"
        onClick={() => onChange({ ...filter, qualifyingOnly: !filter.qualifyingOnly })}
      />

      {active && (
        <button
          type="button"
          onClick={() => onChange(EMPTY_FILTER)}
          className="text-caption text-text-3 transition-colors duration-fast hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          Clear
        </button>
      )}
    </div>
  );
}

function Chip({
  label,
  count,
  dot,
  active,
  palette,
  onClick,
}: {
  label: string;
  count: number;
  dot: string;
  active: boolean;
  palette: "accent" | "qualify";
  onClick: () => void;
}) {
  // Qualifying is a score statement, not a selection — it uses the qualify palette
  // when active, not the accent (design lines 699–702).
  const activeClass =
    palette === "qualify"
      ? "border-qualify bg-qualify-soft text-qualify"
      : "border-accent bg-accent-soft text-accent";

  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-pill border px-3 py-1 text-caption transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 ${
        active ? activeClass : "border-border bg-surface text-text-2 hover:text-text"
      }`}
    >
      <span className={`h-[7px] w-[7px] rounded-pill ${dot}`} aria-hidden="true" />
      {label}
      <span className="font-mono">{count}</span>
    </button>
  );
}
