// A small "differs from .env" indicator (ADR-031). Shown when a stored value has
// diverged from its .env seed, so the user knows the DB — not the file — is winning.

export function DiffBadge({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <span className="rounded-pill bg-nearmiss-soft px-2 py-0.5 font-mono text-label uppercase tracking-[0.05em] text-nearmiss">
      differs from .env
    </span>
  );
}
