import { useState } from "react";

import type { RunOut } from "../api/client";
import { isRunDone, useRun, useStartRun } from "../hooks/useRuns";

// "Run search now" (W8): kick the same multi-profile pipeline a scheduled fire runs,
// without waiting for cron. A run is async — the button starts it, then the run-status
// dot reflects the live poll (running → delivered / zero results / failed), matching
// the design's run-status dot vocabulary. On success the job list refetches itself
// (handled in useRun), so new results appear here without a manual reload.

type DotState = "running" | "delivered" | "zero" | "failed";

const DOT: Record<DotState, { color: string; label: string }> = {
  running: { color: "bg-accent", label: "Running search…" },
  delivered: { color: "bg-qualify", label: "Search delivered" },
  zero: { color: "bg-nearmiss", label: "No qualifying results" },
  failed: { color: "bg-danger", label: "Run failed" },
};

/** Map a run's state to a status dot; null when there is nothing to show. */
function dotState(
  run: RunOut | undefined,
  pending: boolean,
): DotState | null {
  if (pending || run?.status === "running") return "running";
  if (run?.status === "failed") return "failed";
  if (run?.status === "succeeded") return run.qualifying > 0 ? "delivered" : "zero";
  return null;
}

export function RunButton() {
  const [runId, setRunId] = useState<string | null>(null);
  const start = useStartRun();
  const { data: run } = useRun(runId);

  const busy = start.isPending || run?.status === "running";
  const state = dotState(run, start.isPending);
  const done = isRunDone(run);

  function onClick() {
    if (busy) return;
    start.mutate(undefined, {
      onSuccess: (started) => setRunId(started.id),
    });
  }

  return (
    <div className="flex items-center gap-3">
      {state && (
        <span
          className="flex items-center gap-2 text-small text-text-2"
          role="status"
          aria-live="polite"
          data-testid="run-status"
        >
          <span
            className={`h-2 w-2 rounded-pill ${DOT[state].color}`}
            aria-hidden="true"
          />
          {DOT[state].label}
          {done && run && (
            <span className="font-mono text-text-3">
              {run.status === "succeeded"
                ? `${run.qualifying}/${run.jobsFound}`
                : run.error}
            </span>
          )}
        </span>
      )}
      {start.isError && !busy && (
        <span className="text-small text-danger" role="alert">
          {start.error.message}
        </span>
      )}
      <button
        type="button"
        onClick={onClick}
        disabled={busy}
        title="Runs every enabled profile, not just the one you're viewing"
        className="rounded-control bg-accent px-3 py-1.5 text-control text-accent-on transition-colors duration-fast hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-60"
      >
        {busy ? "Running…" : "Run search now"}
      </button>
    </div>
  );
}
