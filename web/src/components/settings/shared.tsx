// Shared styling constants + small building blocks for the settings panels.
// Tokens only (design rules): one btn-primary per view, visible focus rings,
// transitions limited to background/border-color within the motion budget.

export const inputClass =
  "w-full rounded-control border border-border-strong bg-bg px-3 py-2 text-control text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2";
export const selectClass = inputClass;
export const primaryClass =
  "rounded-control bg-accent px-4 py-2 text-control text-accent-on transition-colors duration-fast hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-60";
export const secondaryClass =
  "rounded-control border border-border-strong px-3 py-2 text-control text-text transition-colors duration-fast hover:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-60";
export const ghostClass =
  "rounded-control px-3 py-2 text-control text-accent transition-colors duration-fast hover:text-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2";
export const dangerClass =
  "rounded-control border border-danger px-3 py-2 text-control text-danger transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2";

export function PanelHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header>
      <h2 className="font-display text-h2">{title}</h2>
      <p className="mt-1 max-w-prose text-small text-text-2">{subtitle}</p>
    </header>
  );
}

export function Field({
  label,
  htmlFor,
  hint,
  children,
}: {
  label: string;
  htmlFor: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="max-w-md">
      <label htmlFor={htmlFor} className="block text-label font-semibold text-text">
        {label}
      </label>
      <div className="mt-1.5">{children}</div>
      {hint && <p className="mt-1 text-caption text-text-3">{hint}</p>}
    </div>
  );
}

export function PanelStatus({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-small text-text-2" role="status" aria-live="polite">
      {children}
    </p>
  );
}

export function PanelError() {
  return (
    <div className="rounded-card border border-border bg-surface p-6 text-small text-text-2">
      Couldn’t load settings. Check that the API is running.
    </div>
  );
}
