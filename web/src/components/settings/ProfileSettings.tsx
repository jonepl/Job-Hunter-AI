import { useState } from "react";

import type { ProfileIn, ProfileOut } from "../../api/client";
import {
  useCreateProfile,
  useDeleteProfile,
  useProfiles,
  useUpdateProfile,
} from "../../hooks/useProfiles";
import { useSettings } from "../../hooks/useSettings";
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
  };
}

export function ProfileSettings() {
  const { data: profiles, isLoading, isError } = useProfiles();
  const create = useCreateProfile();
  const update = useUpdateProfile();
  const remove = useDeleteProfile();
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

              {/* Meta — platforms + last run. */}
              <div className="flex flex-col items-end gap-[3px] text-right">
                <span className="text-small text-text-2">
                  {platformLine(p.activeScrapers)}
                </span>
                <span className="font-mono text-label text-text-3">{lastRunText(p)}</span>
              </div>

              {/* Actions — edit, pause/resume, delete. */}
              <div className="flex gap-1.5">
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
