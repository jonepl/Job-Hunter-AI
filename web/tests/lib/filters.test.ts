import {
  EMPTY_FILTER,
  applyFilters,
  isFilterActive,
  labelCount,
  qualifyingCount,
  savedCount,
  toggleLabel,
} from "../../src/lib/filters";
import { makeJob } from "../helpers";

const jobs = [
  makeJob({ id: 1, status: "applied", score: 90, threshold: 70, nearMissFloor: 55 }), // qualify
  makeJob({ id: 2, status: "applied", score: 60, threshold: 70, nearMissFloor: 55 }), // near-miss
  makeJob({ id: 3, status: "interviewing", score: 80, threshold: 70, nearMissFloor: 55 }), // qualify
  makeJob({ id: 4, status: "not_interested", score: 40, threshold: 70, nearMissFloor: 55, saved: true }),
  makeJob({ id: 5, status: "evaluated", score: 95, threshold: 70, nearMissFloor: 55, saved: true }), // qualify
];

describe("filter model", () => {
  it("the empty filter matches every job", () => {
    expect(applyFilters(jobs, EMPTY_FILTER)).toHaveLength(jobs.length);
    expect(isFilterActive(EMPTY_FILTER)).toBe(false);
  });

  it("OR-s label chips together", () => {
    const ids = applyFilters(jobs, { ...EMPTY_FILTER, labels: ["applied", "interviewing"] }).map(
      (job) => job.id,
    );
    expect(ids).toEqual([1, 2, 3]);
  });

  it("AND-s qualifying-only with the labels", () => {
    const ids = applyFilters(jobs, { labels: ["applied"], qualifyingOnly: true, saved: false }).map(
      (job) => job.id,
    );
    // Only #1 is both applied AND qualifying (#2 is applied but a near-miss).
    expect(ids).toEqual([1]);
  });

  it("AND-s the saved toggle", () => {
    const ids = applyFilters(jobs, { ...EMPTY_FILTER, saved: true }).map((job) => job.id);
    expect(ids).toEqual([4, 5]);
  });

  it("draws counts from the unfiltered base list", () => {
    expect(labelCount(jobs, "applied")).toBe(2);
    expect(labelCount(jobs, "interviewing")).toBe(1);
    expect(savedCount(jobs)).toBe(2);
    expect(qualifyingCount(jobs)).toBe(3); // #1, #3, #5
  });

  it("counts are independent of any active filter", () => {
    // Applying a filter never changes what the base-list counts report.
    applyFilters(jobs, { ...EMPTY_FILTER, saved: true });
    expect(labelCount(jobs, "applied")).toBe(2);
    expect(qualifyingCount(jobs)).toBe(3);
  });

  it("toggleLabel adds then removes a status immutably", () => {
    const once = toggleLabel(EMPTY_FILTER, "applied");
    expect(once.labels).toEqual(["applied"]);
    const twice = toggleLabel(once, "applied");
    expect(twice.labels).toEqual([]);
    expect(EMPTY_FILTER.labels).toEqual([]); // original untouched
  });
});
