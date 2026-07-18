import type { HumanStatus } from "../api/client";
import {
  HUMAN_STATUSES,
  isHumanStatus,
  isTerminalStatus,
  statusLabel,
} from "../lib/status";

// The status selector (ui-spec §5.5). Six selectable human statuses; a machine
// status shows as the current value (a disabled option) but is never offered.
// Two obligations from ui-spec §4: selecting the current value is a no-op (the
// native select never fires it), and reactivating a terminal status opens a
// client-side soft confirm before the write.

interface Props {
  value: string;
  onChange: (status: HumanStatus) => void;
  disabled?: boolean;
}

export function StatusDropdown({ value, onChange, disabled = false }: Props) {
  function handleChange(event: React.ChangeEvent<HTMLSelectElement>) {
    const next = event.target.value as HumanStatus;
    if (next === value) return; // no-op — no request, no history row
    if (isTerminalStatus(value) && !isTerminalStatus(next)) {
      const ok = window.confirm(
        `This was marked ${statusLabel(value)} — reactivate as ${statusLabel(next)}?`,
      );
      if (!ok) return; // controlled value snaps the select back
    }
    onChange(next);
  }

  return (
    <select
      value={value}
      onChange={handleChange}
      disabled={disabled}
      aria-label="Job status"
      data-testid="status-dropdown"
      className="rounded-control border border-border-strong bg-bg px-3 py-2 text-control text-text transition-colors duration-fast focus-visible:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-60"
    >
      {!isHumanStatus(value) && (
        // The current machine status: shown as selected, never selectable.
        <option value={value} disabled>
          {statusLabel(value)}
        </option>
      )}
      {HUMAN_STATUSES.map((status) => (
        <option key={status} value={status}>
          {statusLabel(status)}
        </option>
      ))}
    </select>
  );
}
