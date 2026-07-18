// The ★ bookmark toggle beside the status dropdown (ui-spec §4/§5). `saved` is a
// boolean orthogonal to status — a job can be saved and applied. Optimistic write
// is handled by the caller's mutation hook.

interface Props {
  saved: boolean;
  onToggle: (saved: boolean) => void;
  disabled?: boolean;
}

export function SaveStar({ saved, onToggle, disabled = false }: Props) {
  return (
    <button
      type="button"
      onClick={() => onToggle(!saved)}
      disabled={disabled}
      aria-pressed={saved}
      aria-label={saved ? "Saved — click to unsave" : "Save this job"}
      data-testid="save-star"
      className={`rounded-control border px-3 py-2 text-control transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-60 ${
        saved
          ? "border-accent text-accent"
          : "border-border-strong text-text-2 hover:border-accent"
      }`}
    >
      {saved ? "★" : "☆"} Save
    </button>
  );
}
