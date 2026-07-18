import { scoreState, stateLabel, type ScoreState } from "../lib/score";

// Pairs with <ThresholdRail>: mono, 600 weight, pill, a 6px currentColor dot,
// the same three states. Renders "92 · Qualifying" / "71 · Near-miss" / "48 · Below".

const STYLES: Record<ScoreState, string> = {
  qualify: "text-qualify bg-qualify-soft",
  nearmiss: "text-nearmiss bg-nearmiss-soft",
  below: "text-below bg-below-soft",
};

interface Props {
  score: number | null;
  threshold: number | null;
  nearMissFloor: number | null;
}

export function ScoreChip({ score, threshold, nearMissFloor }: Props) {
  const state = scoreState(score, threshold, nearMissFloor);
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-2 rounded-pill px-3 py-1 font-mono text-small font-semibold ${STYLES[state]}`}
      data-testid="score-chip"
      data-state={state}
    >
      <span className="h-[6px] w-[6px] rounded-full bg-current" />
      {score ?? "—"} · {stateLabel[state]}
    </span>
  );
}
