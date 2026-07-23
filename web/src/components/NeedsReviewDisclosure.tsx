import type { GenerationKind } from "../api/client";

// Needs-review disclosure (redesign Part I.3). An amber panel listing the structural
// spots to check in a generated document. Its footer is a PRIVACY STATEMENT, not
// decoration (ADR-034, CLAUDE.md #2): reviewLocations carries structural hints only,
// and document content is NEVER fetched, rendered, or excerpted here.

const KIND_LABEL: Record<GenerationKind, string> = {
  resume: "Tailored resume",
  cover_letter: "Cover letter",
};

interface Props {
  kind: GenerationKind;
  locations: string[];
  onDismiss: () => void;
}

export function NeedsReviewDisclosure({ kind, locations, onDismiss }: Props) {
  return (
    <div
      className="mt-4 rounded-card border border-nearmiss bg-nearmiss-soft p-4"
      data-testid="needs-review-disclosure"
    >
      <div className="flex items-start justify-between gap-3">
        <h4 className="text-h3 font-semibold text-nearmiss">
          <span aria-hidden="true">⚠</span> Check before sending — {KIND_LABEL[kind]}
        </h4>
        <button
          type="button"
          onClick={onDismiss}
          className="text-caption text-text-3 transition-colors duration-fast hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          Dismiss
        </button>
      </div>
      <ul className="mt-3 space-y-1" data-testid="review-locations">
        {locations.map((location) => (
          <li key={location} className="flex items-center gap-2 font-mono text-caption text-text-2">
            <span className="h-[6px] w-[6px] rounded-pill bg-nearmiss" aria-hidden="true" />
            {location}
          </li>
        ))}
      </ul>
      <p className="mt-3 text-caption text-text-3">
        Document content is never shown here — download to review these spots.
      </p>
    </div>
  );
}
