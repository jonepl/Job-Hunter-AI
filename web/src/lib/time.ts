// Relative-time formatting shared by the posting-age line and the run-history rail
// ("just now" · "4 hours ago" · "2 days ago" · "1 week ago"). Returns null for a
// null/unparseable input; the caller decides how absence renders.

/** "1 day ago" / "3 days ago" — pluralize the unit and append " ago". */
function plural(n: number, unit: string): string {
  return `${n} ${unit}${n === 1 ? "" : "s"} ago`;
}

/** Format an ISO timestamp as a coarse relative age, or null when unparseable. */
export function relativeTime(iso: string | null): string | null {
  if (!iso) return null;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return null;

  const minutes = Math.floor((Date.now() - then) / 60_000);
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
