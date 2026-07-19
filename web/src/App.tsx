import { useState } from "react";

import { JobList } from "./screens/JobList";
import { Settings } from "./screens/Settings";
import { ThemeToggle } from "./components/ThemeToggle";

// A lightweight view switch held in local state — the app has two top-level
// screens (search + settings) and no router yet. W7 can introduce real routing
// when the screen count grows; today this keeps the surface minimal.
type View = "search" | "settings";

export function App() {
  const [view, setView] = useState<View>("search");

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="font-display text-h2">Job Hunter AI</span>
          <div className="flex items-center gap-3">
            {view === "search" && (
              <button
                type="button"
                onClick={() => setView("settings")}
                className="rounded-control border border-border-strong px-3 py-1.5 text-control text-text-2 transition-colors duration-fast hover:border-accent hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
              >
                Settings
              </button>
            )}
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        {view === "search" ? (
          <JobList />
        ) : (
          <Settings onBack={() => setView("search")} />
        )}
      </main>
    </div>
  );
}
