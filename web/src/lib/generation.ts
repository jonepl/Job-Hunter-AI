// The six generation states (redesign Part I.2), derived from GenerationOut.
// Branch on `status` FIRST — `outcome` is null while pending/failed. `repaired` is a
// distinct, non-warning state (the doc is ready and downloadable; a formatting fix
// was applied). Shared by the split-button menu and the status chips.

import type { GenerationOut } from "../api/client";

export type GenState =
  | "none"
  | "generating"
  | "ready"
  | "repaired"
  | "needs_review"
  | "failed";

/** Classify a generation record (or its absence) into one of the six states. */
export function generationState(gen: GenerationOut | undefined): GenState {
  if (!gen) return "none";
  if (gen.status === "pending") return "generating";
  if (gen.status === "failed") return "failed";
  // status === "ready"
  if (gen.outcome === "needs_review") return "needs_review";
  if (gen.outcome === "repaired") return "repaired";
  return "ready";
}

/** True for the states whose document exists and can be downloaded. */
export function isDownloadable(state: GenState): boolean {
  return state === "ready" || state === "repaired" || state === "needs_review";
}
