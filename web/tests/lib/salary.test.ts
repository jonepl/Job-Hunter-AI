import { formatSalary, formatPostedAge } from "../../src/lib/salary";

const base = { salaryMin: null, salaryMax: null, salaryCurrency: "USD", salaryPeriod: "YEAR" };

describe("formatSalary", () => {
  it("formats a full annual range with k-scaling", () => {
    expect(formatSalary({ ...base, salaryMin: 140000, salaryMax: 175000 })).toBe("$140k–$175k");
  });

  it("formats a min-only range with a trailing plus", () => {
    expect(formatSalary({ ...base, salaryMin: 140000 })).toBe("$140k+");
  });

  it("formats a max-only range as 'Up to'", () => {
    expect(formatSalary({ ...base, salaryMax: 175000 })).toBe("Up to $175k");
  });

  it("returns null when neither bound is known", () => {
    expect(formatSalary(base)).toBeNull();
  });

  it("formats an hourly rate with a /hr suffix and no k-scaling", () => {
    expect(
      formatSalary({ salaryMin: 85, salaryMax: null, salaryCurrency: "USD", salaryPeriod: "HOUR" }),
    ).toBe("$85+/hr");
    expect(
      formatSalary({ salaryMin: 85, salaryMax: 95, salaryCurrency: "USD", salaryPeriod: "HOUR" }),
    ).toBe("$85–$95/hr");
  });

  it("uses a non-USD currency symbol", () => {
    expect(
      formatSalary({ salaryMin: 90000, salaryMax: null, salaryCurrency: "GBP", salaryPeriod: "YEAR" }),
    ).toBe("£90k+");
  });
});

describe("formatPostedAge", () => {
  it("returns null when postedAt is null", () => {
    expect(formatPostedAge(null)).toBeNull();
  });

  it("returns null for an unparseable date", () => {
    expect(formatPostedAge("not-a-date")).toBeNull();
  });

  it("formats hours ago", () => {
    const fourHoursAgo = new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString();
    expect(formatPostedAge(fourHoursAgo)).toBe("4 hours ago");
  });

  it("formats a single day without pluralizing", () => {
    const oneDayAgo = new Date(Date.now() - 26 * 60 * 60 * 1000).toISOString();
    expect(formatPostedAge(oneDayAgo)).toBe("1 day ago");
  });

  it("formats weeks ago", () => {
    const twoWeeksAgo = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString();
    expect(formatPostedAge(twoWeeksAgo)).toBe("2 weeks ago");
  });
});
