import {
  cronToSchedule,
  describeSchedule,
  scheduleToCron,
  type ScheduleModel,
} from "../../src/lib/cron";

describe("scheduleToCron", () => {
  it("builds a daily cron at the chosen time", () => {
    expect(scheduleToCron({ frequency: "daily", time: "08:30", daysOfWeek: [] })).toBe(
      "30 8 * * *",
    );
  });

  it("builds a weekdays cron (1-5)", () => {
    expect(scheduleToCron({ frequency: "weekdays", time: "09:00", daysOfWeek: [] })).toBe(
      "0 9 * * 1-5",
    );
  });

  it("builds a weekly cron from selected days, sorted and de-duplicated", () => {
    expect(
      scheduleToCron({ frequency: "weekly", time: "07:15", daysOfWeek: [5, 1, 1, 3] }),
    ).toBe("15 7 * * 1,3,5");
  });

  it("falls back to every day when a weekly selection is empty", () => {
    expect(scheduleToCron({ frequency: "weekly", time: "06:00", daysOfWeek: [] })).toBe(
      "0 6 * * *",
    );
  });
});

describe("cronToSchedule", () => {
  it("parses a daily cron", () => {
    expect(cronToSchedule("30 8 * * *")).toEqual({
      frequency: "daily",
      time: "08:30",
      daysOfWeek: [],
    });
  });

  it("parses a weekdays cron", () => {
    expect(cronToSchedule("0 9 * * 1-5")).toEqual({
      frequency: "weekdays",
      time: "09:00",
      daysOfWeek: [1, 2, 3, 4, 5],
    });
  });

  it("parses a weekly comma-list cron, sorted", () => {
    expect(cronToSchedule("15 7 * * 5,1,3")).toEqual({
      frequency: "weekly",
      time: "07:15",
      daysOfWeek: [1, 3, 5],
    });
  });

  it("round-trips builder models back to identical cron", () => {
    // daysOfWeek reflects the codec's normalized parse output (weekdays → 1-5).
    const models: ScheduleModel[] = [
      { frequency: "daily", time: "00:00", daysOfWeek: [] },
      { frequency: "weekdays", time: "23:59", daysOfWeek: [1, 2, 3, 4, 5] },
      { frequency: "weekly", time: "12:05", daysOfWeek: [0, 6] },
    ];
    for (const m of models) {
      expect(cronToSchedule(scheduleToCron(m))).toEqual(m);
    }
  });

  it.each([
    ["*/15 * * * *", "step minute"],
    ["0 8 1 * *", "day-of-month set"],
    ["0 8 * 6 *", "month set"],
    ["0 8 * * 1-3", "weekday range other than 1-5"],
    ["0 8 * *", "too few fields"],
    ["not a cron", "garbage"],
    ["60 8 * * *", "minute out of range"],
    ["0 24 * * *", "hour out of range"],
  ])("returns null for a non-representable cron (%s — %s)", (cron) => {
    expect(cronToSchedule(cron)).toBeNull();
  });
});

describe("describeSchedule", () => {
  it("summarizes each frequency", () => {
    expect(describeSchedule({ frequency: "daily", time: "08:00", daysOfWeek: [] })).toBe(
      "Daily at 08:00",
    );
    expect(describeSchedule({ frequency: "weekdays", time: "08:00", daysOfWeek: [] })).toBe(
      "Weekdays at 08:00",
    );
    expect(
      describeSchedule({ frequency: "weekly", time: "08:00", daysOfWeek: [1, 3] }),
    ).toBe("Weekly on Mon, Wed at 08:00");
  });
});
