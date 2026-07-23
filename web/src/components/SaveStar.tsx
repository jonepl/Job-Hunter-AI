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
      className={`flex h-10 w-10 items-center justify-center rounded-control border text-control transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-60 ${
        saved
          ? "border-nearmiss bg-nearmiss-soft text-nearmiss"
          : "border-border-strong text-text-3 hover:border-accent"
      }`}
    >
      {saved ? "★" : "☆"}
    </button>
  );
}
