import { statusGroup, statusLabel, type StatusGroup } from "../lib/status";

// The nine-state status badge with its visual grouping (ui-spec §5.2): machine
// states are muted, the active pipeline carries the accent, offer is celebratory,
// and terminal states are subdued. Color is never decorative.

const GROUP_STYLES: Record<StatusGroup, string> = {
  machine: "bg-surface-2 text-text-3",
  active: "bg-accent-soft text-accent",
  offer: "bg-qualify-soft text-qualify",
  terminal: "bg-surface-2 text-text-2",
};

interface Props {
  status: string;
}

export function StatusPill({ status }: Props) {
  const group = statusGroup(status);
  return (
    <span
      className={`rounded-pill px-2 py-0.5 font-mono text-label uppercase tracking-[0.05em] ${GROUP_STYLES[group]}`}
      data-testid="status-pill"
      data-group={group}
    >
      {statusLabel(status)}
    </span>
  );
}
