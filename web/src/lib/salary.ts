// Salary + posting-age formatting, shared by <JobCard> and the detail meta grid so
// the two never disagree (Part A.6). Both helpers return `null` when nothing is
// known — never "—" or "Unknown". The *caller* decides how absence renders: the
// card omits the segment, the meta grid shows "—".

/** Currency-code → symbol; unknown codes fall back to the code, null to "$". */
const CURRENCY_SYMBOL: Record<string, string> = {
  USD: "$",
  CAD: "$",
  AUD: "$",
  EUR: "€",
  GBP: "£",
};

interface SalaryFields {
  salaryMin: number | null;
  salaryMax: number | null;
  salaryCurrency: string | null;
  salaryPeriod: string | null;
}

/** The trailing period marker ("/hr", "/mo", or "" for annual/unknown). */
function periodSuffix(period: string | null): string {
  switch ((period ?? "").toUpperCase()) {
    case "HOUR":
      return "/hr";
    case "MONTH":
      return "/mo";
    default:
      return "";
  }
}

/** One salary bound as symbol + number: annual "k"-scaled, hourly/monthly raw. */
function amount(value: number, symbol: string, period: string | null): string {
  const p = (period ?? "").toUpperCase();
  if (p === "HOUR") return `${symbol}${value}`;
  if (p === "MONTH") return `${symbol}${value.toLocaleString()}`;
  // Annual (or unknown period) reads best "k"-scaled: 140000 → "140k".
  return `${symbol}${Math.round(value / 1000)}k`;
}

/**
 * Format a salary range: "$140k–$175k" · "$140k+" · "Up to $175k" · "$85/hr".
 * Returns null when neither bound is known — the caller decides how that renders.
 */
export function formatSalary(job: SalaryFields): string | null {
  const { salaryMin, salaryMax, salaryCurrency, salaryPeriod } = job;
  if (salaryMin === null && salaryMax === null) return null;

  const symbol = salaryCurrency
    ? (CURRENCY_SYMBOL[salaryCurrency.toUpperCase()] ?? `${salaryCurrency} `)
    : "$";
  const sfx = periodSuffix(salaryPeriod);
  const fmt = (n: number) => amount(n, symbol, salaryPeriod);

  if (salaryMin !== null && salaryMax !== null) {
    return `${fmt(salaryMin)}–${fmt(salaryMax)}${sfx}`;
  }
  if (salaryMin !== null) {
    return `${fmt(salaryMin)}+${sfx}`;
  }
  // max-only
  return `Up to ${fmt(salaryMax as number)}${sfx}`;
}

/**
 * Format a posting timestamp as a relative age: "2 days ago" · "4 hours ago" ·
 * "1 week ago". Returns null when postedAt is null or unparseable.
 */
export function formatPostedAge(postedAt: string | null): string | null {
  if (!postedAt) return null;
  const then = new Date(postedAt).getTime();
  if (Number.isNaN(then)) return null;

  const diffMs = Date.now() - then;
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return plural(minutes, "minute");

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return plural(hours, "hour");

  const days = Math.floor(hours / 24);
  if (days < 7) return plural(days, "day");

  const weeks = Math.floor(days / 7);
  if (weeks < 5) return plural(weeks, "week");

  const months = Math.floor(days / 30);
  if (months < 12) return plural(months, "month");

  return plural(Math.floor(days / 365), "year");
}

/** "1 day ago" / "3 days ago" — pluralize the unit and append " ago". */
function plural(n: number, unit: string): string {
  return `${n} ${unit}${n === 1 ? "" : "s"} ago`;
}
