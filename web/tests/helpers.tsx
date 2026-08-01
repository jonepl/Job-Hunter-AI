import type { ReactElement, ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { render } from "@testing-library/react";

import type {
  GenerationOut,
  JobDetail,
  JobSummary,
  ProfileOut,
  ResumeOut,
  ResumeState,
  RunOut,
  ScoreCategoryRow,
  SecretStatus,
  SettingsOut,
} from "../src/api/client";

/** A fresh, retry-free QueryClient for a single test render. */
function makeTestClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

/** Render a component wrapped in a fresh (retry-free) React Query provider. */
export function renderWithClient(ui: ReactElement) {
  const client = makeTestClient();
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, ...render(ui, { wrapper }) };
}

/**
 * Render a routing-aware component inside a memory router (+ a fresh QueryClient),
 * so `useSearch` / `useParams` / `useNavigate` resolve. `ui` mounts at both the
 * search route ("/") and the settings route ("/settings/$section"); `initialEntries`
 * selects which one is active (default "/"). Screens that read/write the URL
 * selection get the same behavior they have in production.
 */
export async function renderWithRouter(
  ui: ReactElement,
  { initialEntries = ["/"] }: { initialEntries?: string[] } = {},
) {
  const client = makeTestClient();
  const Component = () => ui;
  const rootRoute = createRootRoute({ component: Outlet });
  const indexRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/",
    validateSearch: (search: Record<string, unknown>) => ({
      view: search.view === "tracked" ? ("tracked" as const) : undefined,
      profile: typeof search.profile === "number" ? search.profile : undefined,
    }),
    component: Component,
  });
  const settingsRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/settings/$section",
    component: Component,
  });
  const routeTree = rootRoute.addChildren([indexRoute, settingsRoute]);
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries }),
  });
  // Resolve the initial match up front so the first render is populated — otherwise
  // RouterProvider paints empty and settles a tick later, breaking synchronous queries.
  await router.load();
  return {
    client,
    router,
    ...render(
      <QueryClientProvider client={client}>
        {/* The ad-hoc test router differs from the registered app router type. */}
        <RouterProvider router={router as never} />
      </QueryClientProvider>,
    ),
  };
}

/** Build a JobSummary fixture with sensible defaults; override any field. */
export function makeJob(overrides: Partial<JobSummary> = {}): JobSummary {
  return {
    id: 1,
    title: "Senior Software Engineer",
    company: "Acme Corp",
    location: "Remote",
    url: "https://example.com/jobs/1",
    platforms: ["linkedin"],
    score: 82,
    threshold: 70,
    nearMissFloor: 55,
    hireRecommendation: "Yes",
    seniorityLevel: "Senior",
    status: "evaluated",
    saved: false,
    salaryMin: 140000,
    salaryMax: 175000,
    salaryCurrency: "USD",
    salaryPeriod: "YEAR",
    postedAt: "2026-07-12T09:00:00",
    lastSeenAt: "2026-07-14T09:00:00",
    ...overrides,
  };
}

const CATEGORIES = [
  "role_alignment",
  "technical_stack_match",
  "system_design_architecture",
  "impact_and_metrics",
  "domain_industry_experience",
  "problem_space_relevance",
  "ownership_and_leadership",
  "resume_signal_quality",
  "career_trajectory",
];

function makeBreakdown(): ScoreCategoryRow[] {
  return CATEGORIES.map((category) => ({
    category,
    earned: 8,
    max: 10,
    reasoning: "ok",
  }));
}

/** Build a JobDetail fixture with sensible defaults; override any field. */
export function makeJobDetail(overrides: Partial<JobDetail> = {}): JobDetail {
  return {
    id: 1,
    title: "Senior Software Engineer",
    company: "Acme Corp",
    location: "Remote",
    url: "https://example.com/jobs/1",
    description: "Own end-to-end design for our core product.",
    platforms: ["linkedin", "indeed"],
    score: 82,
    threshold: 70,
    nearMissFloor: 55,
    hireRecommendation: "Yes",
    seniorityLevel: "Senior",
    yearsExperienceDetected: 8,
    summary: "Strong fit.",
    matchedSkills: ["Python", "FastAPI"],
    missingSkills: ["Kubernetes"],
    scoreBreakdown: makeBreakdown(),
    status: "evaluated",
    saved: false,
    salaryMin: 140000,
    salaryMax: 175000,
    salaryCurrency: "USD",
    salaryPeriod: "YEAR",
    employmentType: "FULLTIME",
    postedAt: "2026-07-12T09:00:00",
    statusHistory: [
      { fromStatus: null, toStatus: "evaluated", note: null, changedAt: "2026-07-14T09:00:00" },
    ],
    generations: [],
    lastSeenAt: "2026-07-14T09:00:00",
    ...overrides,
  };
}

/** Build a ResumeOut (one stored version) fixture; override any field. */
export function makeResume(overrides: Partial<ResumeOut> = {}): ResumeOut {
  return {
    version: 1,
    filename: "avery-reyes_master-resume.pdf",
    sizeBytes: 214_000,
    skillCount: 41,
    roleCount: 5,
    isActive: true,
    uploadedAt: "2026-06-28T09:00:00",
    ...overrides,
  };
}

/** Build a ResumeState (active + version history) from the given versions. */
export function makeResumeState(overrides: Partial<ResumeState> = {}): ResumeState {
  const versions = overrides.versions ?? [makeResume()];
  const active = overrides.active ?? versions.find((v) => v.isActive) ?? null;
  return { active, versions, ...overrides };
}

/** Build a GenerationOut fixture (a ready resume by default); override any field. */
export function makeGeneration(overrides: Partial<GenerationOut> = {}): GenerationOut {
  return {
    id: "gen-abc123",
    jobId: 1,
    kind: "resume",
    status: "ready",
    outcome: "clean",
    reviewLocations: [],
    repairNote: "",
    createdAt: "2026-07-05T09:00:00",
    ...overrides,
  };
}

/** Build a SecretStatus fixture (configured, not overridden); override any field. */
export function makeSecretStatus(overrides: Partial<SecretStatus> = {}): SecretStatus {
  return {
    name: "openai_api_key",
    configured: true,
    masked: "1234",
    overridden: false,
    ...overrides,
  };
}

/** Build a SettingsOut fixture with sensible defaults; override any field. */
export function makeSettings(overrides: Partial<SettingsOut> = {}): SettingsOut {
  const voice = { tone: "direct", person: "first_person", styleNotes: "" } as const;
  return {
    evaluatorProvider: "openai",
    evaluatorModel: null,
    enrichmentMode: "shadow",
    voice: { ...voice },
    nearMissBand: 15,
    envDefaults: {
      evaluatorProvider: "openai",
      evaluatorModel: null,
      enrichmentMode: "shadow",
      voice: { ...voice },
    },
    secrets: [
      makeSecretStatus({ name: "openai_api_key" }),
      makeSecretStatus({ name: "anthropic_api_key", configured: false, masked: "" }),
      makeSecretStatus({ name: "gemini_api_key" }),
    ],
    pricing: {
      showCostEstimate: false,
      openai: { inputPer1M: 2.5, outputPer1M: 10 },
      anthropic: { inputPer1M: 3, outputPer1M: 15 },
    },
    ...overrides,
  };
}

/** Build a ProfileOut fixture with sensible defaults; override any field. */
export function makeProfile(overrides: Partial<ProfileOut> = {}): ProfileOut {
  return {
    id: 1,
    name: "Backend",
    query: "Senior Software Engineer",
    location: "United States",
    workTypes: ["remote"],
    datePosted: "3days",
    activeScrapers: ["linkedin", "indeed"],
    scoreThreshold: 75,
    topResults: null,
    enabled: true,
    scheduleCron: "",
    scheduleTimezone: "UTC",
    scheduleEnabled: false,
    nextRunAt: null,
    lastRunAt: null,
    lastRunStatus: null,
    ...overrides,
  };
}

/** Build a RunOut fixture with sensible defaults; override any field. */
export function makeRun(overrides: Partial<RunOut> = {}): RunOut {
  return {
    id: "run-abc",
    status: "running",
    trigger: "web",
    profileId: null,
    profilesRun: 0,
    jobsFound: 0,
    newJobs: 0,
    qualifying: 0,
    error: "",
    startedAt: "2026-07-19T09:00:00",
    finishedAt: null,
    ...overrides,
  };
}
