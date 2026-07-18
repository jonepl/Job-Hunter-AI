import type { JobSummary } from "../src/api/client";

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
    lastSeenAt: "2026-07-14T09:00:00",
    ...overrides,
  };
}
