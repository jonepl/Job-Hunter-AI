import {
  Link,
  Outlet,
  createRootRoute,
  createRoute,
  createRouter,
  redirect,
  useRouterState,
} from "@tanstack/react-router";

import { JobList } from "./screens/JobList";
import { Settings } from "./screens/Settings";
import { isSectionId } from "./components/SettingsNav";
import { SearchThresholdIndicator, SearchTopBarCenter } from "./components/SearchTopBar";
import { ThemeToggle } from "./components/ThemeToggle";
import { TopBar } from "./components/TopBar";
import type { SearchParams } from "./lib/searchView";

// Routing lives in the URL so the current screen, Settings section, and Search rail
// selection all survive a reload and are deep-linkable (grilling: theme+route
// persistence). Two top-level screens hang off a shared shell:
//   /                       -> Search (JobList); ?view=tracked / ?profile=<id>
//   /settings               -> redirect to the default section
//   /settings/<section>     -> Settings, that pane
// The shell (TopBar + main outlet) was formerly App.tsx.

const DEFAULT_SECTION = "voice" as const;

/** The gear icon-button — the Search screen's entry point into Settings. */
function SettingsLink() {
  return (
    <Link
      to="/settings/$section"
      params={{ section: DEFAULT_SECTION }}
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
    </Link>
  );
}

/** The shared shell: TopBar (contents keyed to the active screen) + routed main. */
function RootLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const isSearch = !pathname.startsWith("/settings");

  const center = isSearch ? (
    <SearchTopBarCenter />
  ) : (
    <span className="rounded-pill border border-border px-2.5 py-[3px] font-mono text-label uppercase tracking-[0.08em] text-text-3">
      Settings
    </span>
  );

  const right = isSearch ? (
    <>
      <SearchThresholdIndicator />
      <ThemeToggle />
      <SettingsLink />
    </>
  ) : (
    <>
      <Link
        to="/"
        className="text-small font-semibold text-accent transition-colors duration-fast hover:text-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
      >
        ← Back to search
      </Link>
      <ThemeToggle />
    </>
  );

  return (
    <div className="min-h-screen bg-bg">
      <TopBar center={center} right={right} />
      <main>
        <Outlet />
      </main>
    </div>
  );
}

const rootRoute = createRootRoute({ component: RootLayout });

const searchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  validateSearch: (search: Record<string, unknown>): SearchParams => ({
    view: search.view === "tracked" ? "tracked" : undefined,
    profile:
      typeof search.profile === "number" && Number.isFinite(search.profile)
        ? search.profile
        : undefined,
  }),
  component: JobList,
});

const settingsIndexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/settings",
  beforeLoad: () => {
    throw redirect({ to: "/settings/$section", params: { section: DEFAULT_SECTION } });
  },
});

const settingsSectionRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/settings/$section",
  beforeLoad: ({ params }) => {
    if (!isSectionId(params.section)) {
      throw redirect({ to: "/settings/$section", params: { section: DEFAULT_SECTION } });
    }
  },
  component: Settings,
});

const routeTree = rootRoute.addChildren([
  searchRoute,
  settingsIndexRoute,
  settingsSectionRoute,
]);

export const router = createRouter({ routeTree });

// Register the router type so <Link>/navigate get typed routes + params.
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
