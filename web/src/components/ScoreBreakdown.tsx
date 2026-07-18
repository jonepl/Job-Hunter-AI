import type { ScoreCategoryRow } from "../api/client";
import { scoreState, type ScoreState } from "../lib/score";

// The nine-category evaluation breakdown (ui-spec §4). One row per category in
// backend rubric order: a label, a mono earned/max, and a thin bar colored by
// how much of the category was earned. Numbers are mono (design.md).

const BAR: Record<ScoreState, string> = {
  qualify: "bg-qualify",
  nearmiss: "bg-nearmiss",
  below: "bg-below",
};

/** "role_alignment" → "Role alignment". */
function categoryLabel(category: string): string {
  const spaced = category.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export function ScoreBreakdown({ breakdown }: { breakdown: ScoreCategoryRow[] }) {
  return (
    <ul className="space-y-2" data-testid="score-breakdown">
      {breakdown.map((row) => {
        const pct = row.max > 0 ? Math.round((row.earned / row.max) * 100) : 0;
        // Reuse the one score-state rule: earned/max as a 0–100 with a 70 tick.
        const state = scoreState(pct, 70, 40);
        return (
          <li key={row.category} className="flex items-center gap-3" title={row.reasoning}>
            <span className="w-52 shrink-0 text-small text-text-2">
              {categoryLabel(row.category)}
            </span>
            <span className="relative h-[6px] flex-1 rounded-pill bg-surface-2">
              <span
                className={`absolute left-0 top-0 h-[6px] rounded-pill ${BAR[state]}`}
                style={{ width: `${pct}%` }}
              />
            </span>
            <span className="w-12 shrink-0 text-right font-mono text-small text-text">
              {row.earned}/{row.max}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
