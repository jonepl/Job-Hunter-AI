import { useState } from "react";

import { JobList } from "./screens/JobList";
import { Settings } from "./screens/Settings";
import { RunButton } from "./components/RunButton";
import { ThemeToggle } from "./components/ThemeToggle";
import { TopBar } from "./components/TopBar";

// A lightweight view switch held in local state — the app has two top-level
// screens (search + settings) and no router yet. W7 can introduce real routing
// when the screen count grows; today this keeps the surface minimal.
type View = "search" | "settings";

/** The gear icon-button — the Search screen's entry point into Settings. */
function SettingsButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Settings"
      className="rounded-control border border-border-strong p-1.5 text-text-2 transition-colors duration-fast hover:border-accent hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
    >
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-[18px] w-[18px]"
      >
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1.08 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    </button>
  );
}

export function App() {
  const [view, setView] = useState<View>("search");
  const isSearch = view === "search";

  // The Search top bar's center is the run control for now; the full design
  // center (active-profile box + threshold indicator) belongs to the Search
  // component plan. Settings shows the mono context pill.
  const center = isSearch ? (
    <RunButton />
  ) : (
    <span className="rounded-pill border border-border px-2.5 py-[3px] font-mono text-label uppercase tracking-[0.08em] text-text-3">
      Settings
    </span>
  );

  const right = isSearch ? (
    <>
      <ThemeToggle />
      <SettingsButton onClick={() => setView("settings")} />
    </>
  ) : (
    <>
      <button
        type="button"
        onClick={() => setView("search")}
        className="text-small font-semibold text-accent transition-colors duration-fast hover:text-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
      >
        ← Back to search
      </button>
      <ThemeToggle />
    </>
  );

  return (
    <div className="min-h-screen bg-bg">
      <TopBar center={center} right={right} />
      <main>{isSearch ? <JobList /> : <Settings />}</main>
    </div>
  );
}
