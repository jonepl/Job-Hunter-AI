// Filtered-empty state (redesign Part F.4): the base list has jobs, but the active
// filters match none. Shows the base-list count and a Clear that resets the filter.

interface Props {
  baseCount: number;
  onClear: () => void;
}

export function FilteredEmpty({ baseCount, onClear }: Props) {
  return (
    <div
      className="rounded-card border border-dashed border-border bg-surface p-8 text-center"
      data-testid="filtered-empty"
    >
      <p className="text-small text-text-2">No jobs match these filters.</p>
      <p className="mt-1 text-caption text-text-3">
        <span className="font-mono">{baseCount}</span>{" "}
        {baseCount === 1 ? "job" : "jobs"} in this view.
      </p>
      <button
        type="button"
        onClick={onClear}
        className="mt-4 rounded-control border border-border-strong bg-surface px-4 py-2 text-control text-text transition-colors duration-fast hover:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
      >
        Clear filters
      </button>
    </div>
  );
}
