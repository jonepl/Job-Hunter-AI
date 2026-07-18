import { scoreState, type ScoreState } from "../lib/score";

// The signature component: a 0–100 track with the score as fill and a tick at
// the active threshold. Reused on every card and (later) the detail pane.
// Geometry from .claude/rules/design.md; color is never decorative.

const FILL: Record<ScoreState, string> = {
  qualify: "bg-qualify",
  nearmiss: "bg-nearmiss",
  below: "bg-below",
};

interface Props {
  score: number | null;
  threshold: number | null;
  nearMissFloor: number | null;
}

const clampPct = (n: number): number => Math.max(0, Math.min(100, n));

export function ThresholdRail({ score, threshold, nearMissFloor }: Props) {
  const state = scoreState(score, threshold, nearMissFloor);
  const fillPct = clampPct(score ?? 0);
  const tickPct = threshold !== null ? clampPct(threshold) : null;

  return (
    // Top padding reserves room for the tick's mono label above the track.
    <div className="relative pt-4" data-testid="threshold-rail" data-state={state}>
      <div className="relative h-[10px] w-full rounded-pill bg-surface-2">
        <div
          className={`absolute left-0 top-0 h-[10px] rounded-pill ${FILL[state]}`}
          style={{ width: `${fillPct}%` }}
          data-testid="threshold-rail-fill"
        />
        {tickPct !== null && (
          <>
            <span
              className="absolute -translate-x-1/2 font-mono text-tick text-text-2"
              style={{ left: `${tickPct}%`, top: "-14px" }}
            >
              {threshold}
            </span>
            {/* 2px --text bar at 55% opacity, overhanging 5px top and bottom. */}
            <div
              className="absolute w-[2px] bg-text"
              style={{ left: `${tickPct}%`, top: "-5px", height: "20px", opacity: 0.55 }}
              data-testid="threshold-rail-tick"
            />
          </>
        )}
      </div>
    </div>
  );
}
