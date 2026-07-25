import type { ReactNode } from "react";
import { Link, useRouterState } from "@tanstack/react-router";

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

/** The logo tile + wordmark. Purely visual; wrapped for the home link below. */
function Identity() {
  return (
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
  );
}

/** Render the shared application top bar with screen-specific slots. */
export function TopBar({ center, right }: TopBarProps) {
  // The identity group returns to the Search screen. When already there, it is
  // inert (rendered as static markup) so clicking the logo does nothing.
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const onHome = pathname === "/";

  return (
    <header className="flex h-[66px] items-center gap-[22px] border-b border-border bg-surface px-6">
      {onHome ? (
        <Identity />
      ) : (
        <Link
          to="/"
          aria-label="Go to search home"
          className="rounded-control focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          <Identity />
        </Link>
      )}
      {center}
      {right && <div className="ml-auto flex items-center gap-4">{right}</div>}
    </header>
  );
}
