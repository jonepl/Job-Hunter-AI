import type { RunOut } from "../../api/client";
import { useTriggerRun } from "../../hooks/useRuns";

// Run-failed panel (redesign Part F.2). Centred, danger heading, the run's bare
// exception *type name* (never a prettified message — schemas.py), and a Retry that
// calls the same run mutation as <RunButton>. No fabricated failure copy.

export function RunFailed({ run }: { run: RunOut }) {
  const trigger = useTriggerRun();

  return (
    <div
      className="rounded-card border border-border bg-surface p-8 text-center"
      data-testid="run-failed"
    >
      <h2 className="font-display text-h3 text-danger">Run failed</h2>
      {run.error && (
        <p className="mx-auto mt-2 max-w-md font-mono text-small text-text-2">{run.error}</p>
      )}
      <button
        type="button"
        onClick={() => trigger.mutate()}
        disabled={trigger.isPending}
        className="mt-4 rounded-control bg-accent px-4 py-2 text-control text-accent-on transition-colors duration-fast hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-60"
      >
        {trigger.isPending ? "Starting…" : "Retry run"}
      </button>
    </div>
  );
}
