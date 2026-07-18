// Minimal status primitive. The full nine-state visual grouping (ui-spec §5.2)
// and the status data itself land with Story C; W1 jobs carry no human status,
// so this is not yet wired into <JobCard>. Kept as the reusable vocabulary.

interface Props {
  status: string;
}

export function StatusPill({ status }: Props) {
  return (
    <span
      className="rounded-pill bg-surface-2 px-2 py-0.5 font-mono text-label uppercase tracking-[0.05em] text-text-2"
      data-testid="status-pill"
    >
      {status}
    </span>
  );
}
