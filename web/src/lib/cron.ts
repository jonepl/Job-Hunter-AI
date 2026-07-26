// Cron codec for the per-profile schedule builder (per-profile-scheduling §D).
//
// The stored source of truth is always the 5-field cron string (APScheduler consumes
// it). The builder UI edits an intuitive ScheduleModel; this codec converts both ways.
// A cron the builder can't represent (e.g. "every 15 minutes") returns null from
// cronToSchedule, which the editor uses to fall back to raw-cron mode. Cron fields:
//
//     ┌ minute  ┌ hour  ┌ day-of-month  ┌ month  ┌ day-of-week (0=Sun … 6=Sat)
//     M         H       DOM             MON       DOW

export type Frequency = "daily" | "weekdays" | "weekly";

export interface ScheduleModel {
  /** How often the run fires. */
  frequency: Frequency;
  /** Time of day as "HH:MM" (24h, zero-padded). */
  time: string;
  /** Selected weekdays (0=Sun … 6=Sat) — only meaningful for "weekly". */
  daysOfWeek: number[];
}

/** A sensible starting model for a freshly enabled schedule (weekdays at 08:00). */
export function defaultSchedule(): ScheduleModel {
  return { frequency: "weekdays", time: "08:00", daysOfWeek: [1, 2, 3, 4, 5] };
}

/** Zero-pad a number to two digits ("8" → "08"). */
function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

/** Parse a plain non-negative integer field, or null if it isn't one. */
function parseIntField(field: string, max: number): number | null {
  if (!/^\d+$/.test(field)) return null;
  const n = Number(field);
  return n >= 0 && n <= max ? n : null;
}

/**
 * Build a cron string from the intuitive model. Always representable, so this never
 * fails; an empty weekly selection falls back to "*" (every day) so the cron stays valid.
 */
export function scheduleToCron(model: ScheduleModel): string {
  const [h, m] = model.time.split(":");
  const minute = Number(m ?? 0);
  const hour = Number(h ?? 0);
  let dow = "*";
  if (model.frequency === "weekdays") {
    dow = "1-5";
  } else if (model.frequency === "weekly") {
    const days = [...new Set(model.daysOfWeek)].sort((a, b) => a - b);
    dow = days.length > 0 ? days.join(",") : "*";
  }
  return `${minute} ${hour} * * ${dow}`;
}

/**
 * Parse a cron string back into the intuitive model, or null when it isn't
 * builder-representable (the editor then shows raw-cron mode). Representable shapes:
 * a fixed minute + hour, any day-of-month/month wildcard, and a day-of-week that is
 * "*", "1-5", or a comma list of single weekdays.
 */
export function cronToSchedule(cron: string): ScheduleModel | null {
  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) return null;
  const [minStr, hourStr, dom, mon, dow] = parts;

  const minute = parseIntField(minStr, 59);
  const hour = parseIntField(hourStr, 23);
  if (minute === null || hour === null) return null;
  if (dom !== "*" || mon !== "*") return null;

  const time = `${pad2(hour)}:${pad2(minute)}`;

  if (dow === "*") {
    return { frequency: "daily", time, daysOfWeek: [] };
  }
  if (dow === "1-5") {
    return { frequency: "weekdays", time, daysOfWeek: [1, 2, 3, 4, 5] };
  }
  // A comma list of single weekdays → weekly. Any range/step token is non-representable.
  const days: number[] = [];
  for (const token of dow.split(",")) {
    const d = parseIntField(token, 6);
    if (d === null) return null;
    days.push(d);
  }
  return { frequency: "weekly", time, daysOfWeek: [...new Set(days)].sort((a, b) => a - b) };
}

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/** A short human summary of a schedule model, e.g. "Weekdays at 08:00". */
export function describeSchedule(model: ScheduleModel): string {
  if (model.frequency === "daily") return `Daily at ${model.time}`;
  if (model.frequency === "weekdays") return `Weekdays at ${model.time}`;
  const days = [...new Set(model.daysOfWeek)]
    .sort((a, b) => a - b)
    .map((d) => DAY_LABELS[d])
    .join(", ");
  return days ? `Weekly on ${days} at ${model.time}` : `Weekly at ${model.time}`;
}

export { DAY_LABELS };
