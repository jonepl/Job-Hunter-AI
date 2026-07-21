import { useState } from "react";

import { useProfiles, useUpdateProfile } from "../../hooks/useProfiles";
import { useSettings } from "../../hooks/useSettings";
import { profileToInput } from "../../lib/settings";
import { Field, PanelError, PanelHeader, PanelStatus, primaryClass, selectClass } from "./shared";

// Match threshold section (ADR-033): the score threshold is stored per profile, so
// this is a profile-scoped editor — pick a profile, drag its threshold, save. It
// writes through the same profile-update path as the full profile editor. The
// near-miss band (NEAR_MISS_BAND) is backend-owned and read-only; it only shades the
// rail and labels the stat cell — never fabricated, never editable here.

export function ThresholdSettings() {
  const { data: profiles, isLoading, isError } = useProfiles();
  // Read-only extra: the near-miss band width. The editor must work without it, so
  // its loading/error state never blocks the slider or save — only the stat grid.
  const { data: settings } = useSettings();
  const update = useUpdateProfile();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [threshold, setThreshold] = useState<number | null>(null);

  if (isLoading) return <PanelStatus>Loading profiles…</PanelStatus>;
  if (isError || !profiles) return <PanelError />;
  if (profiles.length === 0) {
    return (
      <section data-testid="threshold-settings" className="max-w-[640px] space-y-6">
        <PanelHeader title="Match threshold" subtitle="The score a job must reach to qualify." />
        <p className="text-small text-text-2">Add a search profile first.</p>
      </section>
    );
  }

  const selected = profiles.find((p) => p.id === selectedId) ?? profiles[0];
  const value = threshold ?? selected.scoreThreshold;
  const floor = settings ? Math.max(0, value - settings.nearMissBand) : null;

  function save() {
    update.mutate({
      id: selected.id,
      body: { ...profileToInput(selected), scoreThreshold: value },
    });
  }

  return (
    <section data-testid="threshold-settings" className="max-w-[640px] space-y-6">
      <PanelHeader
        title="Match threshold"
        subtitle="Jobs scoring at or above the threshold are delivered as qualifying matches. Lower it to see more near-misses; raise it to cut noise."
      />

      <Field label="Profile" htmlFor="threshold-profile">
        <select
          id="threshold-profile"
          value={selected.id}
          onChange={(e) => {
            setSelectedId(Number(e.target.value));
            setThreshold(null);
          }}
          className={selectClass}
        >
          {profiles.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name || p.query}
            </option>
          ))}
        </select>
      </Field>

      {/* Big mono value + domain caption. */}
      <div className="flex items-baseline justify-between">
        <span
          className="font-mono text-[40px] font-semibold text-qualify"
          data-testid="threshold-value"
        >
          {value}
        </span>
        <span className="font-mono text-caption text-text-3">0–100</span>
      </div>

      {/* Slider — full 0–100 score domain (ADR-033: no unreachable threshold). */}
      <div>
        <label htmlFor="threshold-range" className="block text-label font-semibold text-text">
          Threshold
        </label>
        <input
          id="threshold-range"
          type="range"
          min={0}
          max={100}
          value={value}
          onChange={(e) => setThreshold(Number(e.target.value))}
          aria-label="Threshold"
          className="mt-2 w-full accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
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

      {/* Stat grid — real values only; gated on the settings read so the band is
          never fabricated. The mock's "last run" projection is deferred. */}
      {settings && floor !== null && (
        <div className="grid grid-cols-2 overflow-hidden rounded-card border border-border">
          <div className="border-r border-border p-4">
            <span className="block font-mono text-label uppercase text-text-3">Near-miss band</span>
            <span className="mt-1 block text-body font-semibold text-nearmiss">
              {floor}–{value - 1}
            </span>
          </div>
          <div className="p-4">
            <span className="block font-mono text-label uppercase text-text-3">Applies to</span>
            <span className="mt-1 block text-body font-semibold text-text">
              {selected.name || selected.query}
            </span>
          </div>
        </div>
      )}

      <button type="button" onClick={save} disabled={update.isPending} className={primaryClass}>
        {update.isPending ? "Saving…" : "Save threshold"}
      </button>
    </section>
  );
}
