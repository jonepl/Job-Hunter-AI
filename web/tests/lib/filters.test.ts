import {
  DEFAULT_FILTER,
  JOB_FILTERS,
  countFor,
  filterJobs,
} from "../../src/lib/filters";
import { makeJob } from "../helpers";

const jobs = [
  makeJob({ id: 1, status: "new" }),
  makeJob({ id: 2, status: "evaluated" }),
  makeJob({ id: 3, status: "applied" }),
  makeJob({ id: 4, status: "interviewing" }),
  makeJob({ id: 5, status: "rejected" }),
  makeJob({ id: 6, status: "offer", saved: true }),
  makeJob({ id: 7, status: "evaluated", saved: true }),
];

describe("job filters", () => {
  it("defaults to triage", () => {
    expect(DEFAULT_FILTER).toBe("triage");
  });

  it("triage keeps only new + evaluated", () => {
    const ids = filterJobs(jobs, "triage").map((job) => job.id);
    expect(ids).toEqual([1, 2, 7]);
  });

  it("pipeline keeps only active statuses", () => {
    const ids = filterJobs(jobs, "pipeline").map((job) => job.id);
    expect(ids).toEqual([3, 4]);
  });

  it("all keeps every job", () => {
    expect(filterJobs(jobs, "all")).toHaveLength(jobs.length);
  });

  it("saved keeps only saved jobs", () => {
    const ids = filterJobs(jobs, "saved").map((job) => job.id);
    expect(ids).toEqual([6, 7]);
  });

  it("preserves the source order", () => {
    const ids = filterJobs(jobs, "all").map((job) => job.id);
    expect(ids).toEqual([1, 2, 3, 4, 5, 6, 7]);
  });

  it("countFor matches filterJobs length for every filter", () => {
    for (const filter of JOB_FILTERS) {
      expect(countFor(jobs, filter.id)).toBe(filterJobs(jobs, filter.id).length);
    }
  });
});
