// The generation chip (ui-spec §5.4) is a five-state component, but W2 ships only
// the `empty` state as a disabled stub: document generation (the generations table
// + async endpoints) arrives with Story F. The other four states + polling land
// then. Kept honest — visible but not fake-interactive.

interface Props {
  kind: "resume" | "cover_letter";
}

const LABEL: Record<Props["kind"], string> = {
  resume: "Resume",
  cover_letter: "Cover letter",
};

export function GenerationChip({ kind }: Props) {
  return (
    <span
      className="inline-flex items-center gap-2 rounded-control border border-border bg-surface-2 px-3 py-1.5 text-small text-text-3"
      data-testid="generation-chip"
      data-kind={kind}
      data-state="empty"
      title="Document generation arrives with a later story"
    >
      <span aria-hidden>○</span> {LABEL[kind]}
    </span>
  );
}
