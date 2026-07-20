import type { ReactNode } from "react";

// The shared 66px application top bar. Both top-level screens render the same
// shell — a fixed left identity group (logo tile + wordmark), a screen-specific
// center slot, and a screen-specific right cluster — so the chrome stays put
// when the view switches. Borders define the surface; no shadows (design.md).
//
// The design mock carries an "AR" initials avatar in the right cluster; there is
// no auth or user system here, so that slot holds the ThemeToggle instead.

interface TopBarProps {
  /** Screen-specific middle region, rendered after the identity group. */
  center?: ReactNode;
  /** Screen-specific right cluster, pushed to the far edge. */
  right?: ReactNode;
}

/** Render the shared application top bar with screen-specific slots. */
export function TopBar({ center, right }: TopBarProps) {
  return (
    <header className="flex h-[66px] items-center gap-[22px] border-b border-border bg-surface px-6">
      <div className="flex items-center gap-[9px]">
        <div
          aria-hidden="true"
          className="flex h-[26px] w-[26px] items-center justify-center rounded-control bg-accent font-display text-[15px] font-bold text-accent-on"
        >
          J
        </div>
        <span className="font-display text-[18px] font-bold tracking-[-0.02em]">
          Job Hunter AI
        </span>
      </div>
      {center}
      {right && <div className="ml-auto flex items-center gap-4">{right}</div>}
    </header>
  );
}
