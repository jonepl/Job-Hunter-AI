// The one score-state rule (ADR-033), shared by <ThresholdRail> and <ScoreChip>
// so the rail fill and the chip never disagree. The band is backend-owned and
// arrives per job as threshold + nearMissFloor.

export type ScoreState = "qualify" | "nearmiss" | "below";

/**
 * Classify a score against its own threshold and near-miss floor.
 * qualify: score >= threshold; nearmiss: nearMissFloor <= score < threshold;
 * below: everything else (including missing data).
 */
export function scoreState(
  score: number | null,
  threshold: number | null,
  nearMissFloor: number | null,
): ScoreState {
  if (score === null || threshold === null) return "below";
  if (score >= threshold) return "qualify";
  if (nearMissFloor !== null && score >= nearMissFloor) return "nearmiss";
  return "below";
}

export const stateLabel: Record<ScoreState, string> = {
  qualify: "Qualifying",
  nearmiss: "Near-miss",
  below: "Below",
};
