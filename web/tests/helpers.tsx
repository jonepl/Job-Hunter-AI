import type {
  JobDetail,
  JobSummary,
  ResumeOut,
  ResumeState,
  ScoreCategoryRow,
} from "../src/api/client";

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
