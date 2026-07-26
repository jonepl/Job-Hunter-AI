import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api, type ProfileIn, type ProfileOut, type SchedulePreview } from "../../api/client";
import {
  useCreateProfile,
  useDeleteProfile,
  useProfiles,
  useUpdateProfile,
} from "../../hooks/useProfiles";
import { useRunProfile } from "../../hooks/useRuns";
import { useSettings } from "../../hooks/useSettings";
import {
  DAY_LABELS,
  cronToSchedule,
  defaultSchedule,
  describeSchedule,
  scheduleToCron,
  type Frequency,
  type ScheduleModel,
} from "../../lib/cron";
import { profileToInput } from "../../lib/settings";
import {
  Field,
  PanelError,
  PanelHeader,
  PanelStatus,
  dangerClass,
  ghostClass,
  inputClass,
  primaryClass,
  secondaryClass,
  selectClass,
} from "./shared";

// Search profiles section: full CRUD over the search definitions the run pipeline
// iterates (ADR-031). A list with edit/delete, and an editor form for the per-profile
// search fields. The last remaining profile cannot be deleted (server enforces 409).

const WORK_TYPES = ["remote", "hybrid", "onsite"] as const;
const SCRAPERS = ["linkedin", "indeed", "glassdoor", "ziprecruiter"] as const;
const DATES = [
  { value: "24h", label: "Past 24h" },
  { value: "3days", label: "Past 3 days" },
  { value: "week", label: "Past week" },
  { value: "month", label: "Past month" },
];

// Scraper key → the display name the mock shows in the per-row platforms line.
const PLATFORM_NAMES: Record<string, string> = {
  linkedin: "LinkedIn",
  indeed: "Indeed",
  glassdoor: "Glassdoor",
  ziprecruiter: "ZipRecruiter",
};

/** The platforms a profile searches, derived from its scrapers (e.g. "LinkedIn · Indeed"). */
function platformLine(scrapers: string[]): string {
  return scrapers.map((s) => PLATFORM_NAMES[s] ?? s).join(" · ");
}

/** Format an ISO timestamp as a short "Jul 20, 09:00" run stamp. */
function formatRunTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** The mock's last-run text: paused, running now, a timestamp, or "never run". */
function lastRunText(p: ProfileOut): string {
  if (!p.enabled) return "Paused";
  if (p.lastRunStatus === "running") return "running now";
  if (p.lastRunAt) return formatRunTime(p.lastRunAt);
  return "never run";
}

/** The per-profile schedule status line ("Scheduled — Weekdays at 08:00" / "Not scheduled"). */
function scheduleText(p: ProfileOut): string {
  if (!p.scheduleEnabled || !p.scheduleCron) return "Not scheduled";
  const model = cronToSchedule(p.scheduleCron);
  return model ? `Scheduled — ${describeSchedule(model)}` : `Scheduled — ${p.scheduleCron}`;
}

function blankDraft(): ProfileIn {
  return {
    name: "",
    query: "",
    location: "",
    workTypes: ["remote"],
    datePosted: "3days",
    activeScrapers: [...SCRAPERS],
    scoreThreshold: 75,
    topResults: null,
    enabled: true,
    scheduleCron: "",
    scheduleTimezone: "UTC",
    scheduleEnabled: false,
  };
}

export function ProfileSettings() {
  const { data: profiles, isLoading, isError } = useProfiles();
  const create = useCreateProfile();
  const update = useUpdateProfile();
  const remove = useDeleteProfile();
  const runProfile = useRunProfile();
  const [draft, setDraft] = useState<ProfileIn | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <PanelStatus>Loading profiles…</PanelStatus>;
  if (isError || !profiles) return <PanelError />;

  function startAdd() {
    setEditingId(null);
    setError(null);
    setDraft(blankDraft());
  }

  function startEdit(p: ProfileOut) {
    setEditingId(p.id);
    setError(null);
    setDraft(profileToInput(p));
  }

  function save() {
    if (!draft) return;
    setError(null);
    const onError = (e: Error) => setError(e.message);
    const onSuccess = () => {
      setDraft(null);
      setEditingId(null);
    };
    if (editingId !== null) {
      update.mutate({ id: editingId, body: draft }, { onSuccess, onError });
    } else {
      create.mutate(draft, { onSuccess, onError });
    }
  }

  if (draft) {
    return (
      <ProfileEditor
        draft={draft}
        setDraft={setDraft}
        onSave={save}
        onCancel={() => setDraft(null)}
        saving={create.isPending || update.isPending}
        error={error}
        isNew={editingId === null}
      />
    );
  }

  function togglePause(p: ProfileOut) {
    update.mutate({ id: p.id, body: { ...profileToInput(p), enabled: !p.enabled } });
  }

  return (
    <section data-testid="profile-settings" className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <PanelHeader
          title="Search profiles"
          subtitle="Each profile is a saved query the agent runs on your schedule."
        />
        <button type="button" onClick={startAdd} className={primaryClass}>
          + New profile
        </button>
      </div>

      <ul className="space-y-3" data-testid="profile-list">
        {profiles.map((p) => {
          const name = p.name || p.query;
          return (
            <li
              key={p.id}
              className="flex items-center gap-4 rounded-card border border-border bg-surface p-4"
            >
              {/* Status dot — carries meaning, so it gets an accessible label. */}
              <span
                role="img"
                aria-label={p.enabled ? "Active" : "Paused"}
                className={
                  "h-[9px] w-[9px] shrink-0 rounded-full " +
                  (p.enabled ? "bg-qualify" : "bg-border-strong")
                }
              />

              {/* Identity — dimmed when paused so it reads as inactive at a glance. */}
              <div className={"min-w-0 flex-1 " + (p.enabled ? "" : "text-text-3")}>
                <p className="text-control font-semibold text-text">{name}</p>
                <p className="mt-0.5 truncate font-mono text-caption text-text-3">{p.query}</p>
              </div>

              {/* Meta — platforms, schedule, last run. */}
              <div className="flex flex-col items-end gap-[3px] text-right">
                <span className="text-small text-text-2">
                  {platformLine(p.activeScrapers)}
                </span>
                <span className="font-mono text-label text-text-3">{scheduleText(p)}</span>
                <span className="font-mono text-label text-text-3">{lastRunText(p)}</span>
              </div>

              {/* Actions — run now, edit, pause/resume, delete. */}
              <div className="flex gap-1.5">
                <button
                  type="button"
                  onClick={() => runProfile.mutate(p.id)}
                  disabled={!p.enabled || runProfile.isPending}
                  className={secondaryClass + " disabled:opacity-40"}
                  aria-label={`Run ${name} now`}
                >
                  Run now
                </button>
                <button type="button" onClick={() => startEdit(p)} className={secondaryClass}>
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() => togglePause(p)}
                  disabled={update.isPending}
                  aria-label={`${p.enabled ? "Pause" : "Resume"} ${name}`}
                  className={
                    "rounded-control px-[11px] py-1.5 text-small font-semibold transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 border " +
                    (p.enabled
                      ? "border-border-strong bg-surface text-text-2"
                      : "border-accent bg-accent-soft text-accent")
                  }
                >
                  {p.enabled ? "Pause" : "Resume"}
                </button>
                <button
                  type="button"
                  onClick={() => remove.mutate(p.id)}
                  disabled={profiles.length <= 1 || remove.isPending}
                  className={dangerClass + " disabled:opacity-40"}
                  aria-label={`Delete ${name}`}
                >
                  Delete
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function ProfileEditor({
  draft,
  setDraft,
  onSave,
  onCancel,
  saving,
  error,
  isNew,
}: {
  draft: ProfileIn;
  setDraft: (d: ProfileIn) => void;
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
  error: string | null;
  isNew: boolean;
}) {
  const set = (patch: Partial<ProfileIn>) => setDraft({ ...draft, ...patch });

  function toggle(list: string[] | null | undefined, value: string): string[] {
    const current = list ?? [];
    return current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value];
  }

  return (
    <section data-testid="profile-editor" className="space-y-6">
      <PanelHeader
        title={isNew ? "Add profile" : "Edit profile"}
        subtitle="Define one search the run pipeline executes."
      />

      <Field label="Name" htmlFor="p-name">
        <input id="p-name" value={draft.name ?? ""} onChange={(e) => set({ name: e.target.value })} className={inputClass} />
      </Field>

      <Field label="Query" htmlFor="p-query">
        <input id="p-query" value={draft.query} onChange={(e) => set({ query: e.target.value })} className={inputClass} />
      </Field>

      <Field label="Location" htmlFor="p-location" hint="Optional only when the work type is remote only.">
        <input
          id="p-location"
          value={draft.location ?? ""}
          onChange={(e) => set({ location: e.target.value })}
          className={inputClass}
        />
      </Field>

      <fieldset>
        <legend className="text-label font-semibold text-text">Work types</legend>
        <div className="mt-2 flex flex-wrap gap-3">
          {WORK_TYPES.map((w) => (
            <label key={w} className="flex items-center gap-2 text-small text-text-2">
              <input
                type="checkbox"
                checked={(draft.workTypes ?? []).includes(w)}
                onChange={() => set({ workTypes: toggle(draft.workTypes, w) })}
                className="accent-accent"
              />
              {w}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="text-label font-semibold text-text">Scrapers</legend>
        <div className="mt-2 flex flex-wrap gap-3">
          {SCRAPERS.map((s) => (
            <label key={s} className="flex items-center gap-2 text-small text-text-2">
              <input
                type="checkbox"
                checked={draft.activeScrapers.includes(s)}
                onChange={() => set({ activeScrapers: toggle(draft.activeScrapers, s) })}
                className="accent-accent"
              />
              {s}
            </label>
          ))}
        </div>
      </fieldset>

      <Field label="Date posted" htmlFor="p-date">
        <select
          id="p-date"
          value={draft.datePosted ?? "3days"}
          onChange={(e) => set({ datePosted: e.target.value })}
          className={selectClass}
        >
          {DATES.map((d) => (
            <option key={d.value} value={d.value}>
              {d.label}
            </option>
          ))}
        </select>
      </Field>

      <ThresholdField
        value={draft.scoreThreshold}
        onChange={(v) => set({ scoreThreshold: v })}
      />

      <Field label="Top results" htmlFor="p-top" hint="Blank returns all qualifying results.">
        <input
          id="p-top"
          type="number"
          min={1}
          value={draft.topResults ?? ""}
          onChange={(e) => set({ topResults: e.target.value ? Number(e.target.value) : null })}
          className={inputClass + " font-mono"}
        />
      </Field>

      <ScheduleField
        enabled={draft.scheduleEnabled}
        cron={draft.scheduleCron}
        timezone={draft.scheduleTimezone}
        onChange={(patch) => set(patch)}
      />

      {error && (
        <p className="text-small text-danger" role="alert">
          {error}
        </p>
      )}

      <div className="flex items-center gap-2">
        <button type="button" onClick={onSave} disabled={saving} className={primaryClass}>
          {saving ? "Saving…" : "Save profile"}
        </button>
        <button type="button" onClick={onCancel} className={ghostClass}>
          Cancel
        </button>
      </div>
    </section>
  );
}

/** Debounce a value so the schedule preview query doesn't fire on every keystroke. */
function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

const FREQUENCIES: { value: Frequency; label: string }[] = [
  { value: "daily", label: "Every day" },
  { value: "weekdays", label: "Weekdays (Mon–Fri)" },
  { value: "weekly", label: "Specific days" },
];

/** The IANA timezone list, falling back to a small set where Intl lacks the API (jsdom). */
function timezoneOptions(current: string): string[] {
  const intl = Intl as unknown as { supportedValuesOf?: (k: string) => string[] };
  const zones =
    typeof intl.supportedValuesOf === "function"
      ? intl.supportedValuesOf("timeZone")
      : ["UTC", "America/New_York", "America/Los_Angeles", "Europe/London"];
  return zones.includes(current) ? zones : [current, ...zones];
}

/** The browser's detected timezone, or "UTC" when unavailable. */
function browserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

// Per-profile schedule builder (per-profile-scheduling §D). Cron stays the stored
// source of truth; the intuitive controls (frequency + time + days) generate and parse
// it, with an Advanced (raw cron) escape hatch for expressions the builder can't model.
// A live "Next 3 runs" preview is computed server-side from the generated cron.
function ScheduleField({
  enabled,
  cron,
  timezone,
  onChange,
}: {
  enabled: boolean;
  cron: string;
  timezone: string;
  onChange: (patch: Partial<ProfileIn>) => void;
}) {
  // A cron the builder can't represent forces raw mode; empty cron starts in builder mode.
  const parsed = cronToSchedule(cron);
  const [advanced, setAdvanced] = useState(cron !== "" && parsed === null);
  const [model, setModel] = useState<ScheduleModel>(parsed ?? defaultSchedule());

  const tzValue = timezone || "UTC";
  const debouncedCron = useDebounced(cron, 400);
  const preview = useQuery<SchedulePreview>({
    queryKey: ["profile-schedule-preview", debouncedCron, tzValue],
    queryFn: () => api.getSchedulePreview(debouncedCron, tzValue),
    enabled: enabled && debouncedCron.trim() !== "",
    retry: false,
  });

  function enableSchedule(on: boolean) {
    if (on && cron.trim() === "") {
      const seeded = defaultSchedule();
      setModel(seeded);
      onChange({
        scheduleEnabled: true,
        scheduleCron: scheduleToCron(seeded),
        scheduleTimezone: timezone && timezone !== "UTC" ? timezone : browserTimezone(),
      });
    } else {
      onChange({ scheduleEnabled: on });
    }
  }

  function updateModel(next: ScheduleModel) {
    setModel(next);
    onChange({ scheduleCron: scheduleToCron(next) });
  }

  function toggleDay(day: number) {
    const days = model.daysOfWeek.includes(day)
      ? model.daysOfWeek.filter((d) => d !== day)
      : [...model.daysOfWeek, day];
    updateModel({ ...model, daysOfWeek: days });
  }

  return (
    <section className="space-y-4 rounded-card border border-border p-4" data-testid="schedule-field">
      <label className="flex items-center gap-2 text-control font-semibold text-text">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => enableSchedule(e.target.checked)}
          className="accent-accent"
        />
        Run on a schedule
      </label>

      {enabled && (
        <div className="space-y-4">
          {!advanced ? (
            <>
              <Field label="Frequency" htmlFor="p-sched-freq">
                <select
                  id="p-sched-freq"
                  value={model.frequency}
                  onChange={(e) => updateModel({ ...model, frequency: e.target.value as Frequency })}
                  className={selectClass}
                >
                  {FREQUENCIES.map((f) => (
                    <option key={f.value} value={f.value}>
                      {f.label}
                    </option>
                  ))}
                </select>
              </Field>

              {model.frequency === "weekly" && (
                <fieldset>
                  <legend className="text-label font-semibold text-text">Days</legend>
                  <div className="mt-2 flex flex-wrap gap-3">
                    {DAY_LABELS.map((label, day) => (
                      <label key={label} className="flex items-center gap-2 text-small text-text-2">
                        <input
                          type="checkbox"
                          checked={model.daysOfWeek.includes(day)}
                          onChange={() => toggleDay(day)}
                          className="accent-accent"
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                </fieldset>
              )}

              <Field label="Time of day" htmlFor="p-sched-time">
                <input
                  id="p-sched-time"
                  type="time"
                  value={model.time}
                  onChange={(e) => updateModel({ ...model, time: e.target.value })}
                  className={inputClass + " font-mono"}
                />
              </Field>
            </>
          ) : (
            <Field label="Cron expression" htmlFor="p-sched-cron" hint="Five fields, e.g. 0 8 * * 1-5">
              <input
                id="p-sched-cron"
                value={cron}
                onChange={(e) => onChange({ scheduleCron: e.target.value })}
                placeholder="0 8 * * 1-5"
                className={inputClass + " font-mono"}
              />
            </Field>
          )}

          <Field label="Timezone" htmlFor="p-sched-tz">
            <select
              id="p-sched-tz"
              value={tzValue}
              onChange={(e) => onChange({ scheduleTimezone: e.target.value })}
              className={selectClass + " font-mono"}
            >
              {timezoneOptions(tzValue).map((z) => (
                <option key={z} value={z}>
                  {z}
                </option>
              ))}
            </select>
          </Field>

          {/* Generated cron — the stored value, always visible so the mapping is legible. */}
          <p className="font-mono text-label text-text-3" data-testid="generated-cron">
            Generated cron: <span className="text-text-2">{cron || "—"}</span>
          </p>

          <button
            type="button"
            onClick={() => setAdvanced((a) => !a)}
            className={ghostClass}
          >
            {advanced ? "Use the schedule builder" : "Advanced (raw cron)"}
          </button>

          {/* Live next-runs preview computed server-side (no live scheduler touched). */}
          <div data-testid="schedule-field-preview">
            {debouncedCron.trim() === "" ? (
              <p className="text-small text-text-3">Set a schedule to preview.</p>
            ) : preview.isError ? (
              <p className="text-small text-danger" role="alert">
                Invalid schedule.
              </p>
            ) : preview.data ? (
              <ul className="space-y-1">
                {preview.data.nextRuns.map((iso) => (
                  <li key={iso} className="font-mono text-small text-text-2">
                    {new Date(iso).toLocaleString()}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-small text-text-3">Computing…</p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

// Match threshold editor for the profile form (ADR-033): the score a job must reach
// to qualify, stored per profile. A slider gives feel, the paired mono number box
// gives exact entry, and the qualify-zone rail previews the result live. The
// near-miss band (NEAR_MISS_BAND) is backend-owned and read-only — it only shades
// the rail and labels the stat cell. Its settings read is non-blocking: the slider
// and number always work even if the band is unknown; only the shading + stat cell
// gate on it, so the editor never breaks when useSettings fails.
function ThresholdField({
  value,
  onChange,
}: {
  value: number;
  onChange: (value: number) => void;
}) {
  const { data: settings } = useSettings();
  const floor = settings ? Math.max(0, value - settings.nearMissBand) : null;

  /** Clamp any input to the 0–100 score domain (ADR-033: no unreachable threshold). */
  const clamp = (n: number) => Math.max(0, Math.min(100, n));

  return (
    <div className="max-w-md space-y-3">
      {/* Value + domain caption. The number box is the precise-entry control. */}
      <div className="flex items-baseline justify-between">
        <label htmlFor="p-threshold" className="block text-label font-semibold text-text">
          Score threshold
        </label>
        <span className="font-mono text-caption text-text-3">0–100</span>
      </div>

      <div className="flex items-center gap-4">
        <input
          id="p-threshold-range"
          type="range"
          min={0}
          max={100}
          value={value}
          onChange={(e) => onChange(clamp(Number(e.target.value)))}
          aria-label="Score threshold"
          className="w-full accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        />
        <input
          id="p-threshold"
          type="number"
          min={0}
          max={100}
          value={value}
          onChange={(e) => onChange(clamp(Number(e.target.value)))}
          aria-label="Score threshold value"
          className="w-20 shrink-0 rounded-control border border-border-strong bg-bg px-3 py-2 text-control font-mono text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        />
      </div>

      {/* Qualify-zone rail — presentational; qualify fill threshold→100, near-miss
          band shaded when the (real) band is known, accent tick at the threshold. */}
      <div>
        <div className="relative h-[10px] rounded-pill bg-surface-2">
          {floor !== null && (
            <div
              className="absolute inset-y-0 bg-nearmiss-soft"
              style={{ left: `${floor}%`, width: `${value - floor}%` }}
            />
          )}
          <div
            className="absolute inset-y-0 right-0 rounded-r-pill bg-qualify-soft"
            style={{ left: `${value}%` }}
          />
          <div
            className="absolute -top-[3px] -bottom-[3px] w-[2px] bg-accent"
            style={{ left: `${value}%` }}
          />
        </div>
        <div className="mt-1 flex justify-between font-mono text-label text-text-3">
          <span>0</span>
          <span>100</span>
        </div>
      </div>

      {/* Near-miss band stat — real values only; gated on the settings read so the
          band is never fabricated. */}
      {floor !== null && (
        <div className="overflow-hidden rounded-card border border-border">
          <div className="p-4">
            <span className="block font-mono text-label uppercase text-text-3">Near-miss band</span>
            <span className="mt-1 block text-body font-semibold text-nearmiss">
              {floor}–{value - 1}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
