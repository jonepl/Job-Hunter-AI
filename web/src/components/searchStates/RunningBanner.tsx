// Run-in-progress banner (redesign Part F.1). Renders ABOVE the list — results
// appear as they're scored — not instead of it. The spinner honours
// prefers-reduced-motion (tokens.css handles the reduce case; motion-reduce is a
// belt-and-braces guard).

export function RunningBanner() {
  return (
    <div
      className="mb-4 flex items-center gap-3 rounded-card border border-border bg-surface px-4 py-3"
      role="status"
      aria-live="polite"
      data-testid="running-banner"
    >
      <span
        aria-hidden="true"
        className="inline-block h-4 w-4 shrink-0 animate-spin rounded-pill border-2 border-accent border-t-transparent motion-reduce:animate-none"
      />
      <p className="text-small text-text-2">
        Run in progress — results appear as they’re scored.
      </p>
    </div>
  );
}
