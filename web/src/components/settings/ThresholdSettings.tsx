import { useState } from "react";

import { useProfiles, useUpdateProfile } from "../../hooks/useProfiles";
import { profileToInput } from "../../lib/settings";
import {
  Field,
  PanelError,
  PanelHeader,
  PanelStatus,
  primaryClass,
  selectClass,
} from "./shared";

// Match threshold section (ADR-033): the score threshold is stored per profile, so
// this is a profile-scoped editor — pick a profile, drag its threshold, save. It
// writes through the same profile-update path as the full profile editor.

export function ThresholdSettings() {
  const { data: profiles, isLoading, isError } = useProfiles();
  const update = useUpdateProfile();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [threshold, setThreshold] = useState<number | null>(null);

  if (isLoading) return <PanelStatus>Loading profiles…</PanelStatus>;
  if (isError || !profiles) return <PanelError />;
  if (profiles.length === 0) {
    return (
      <section data-testid="threshold-settings" className="space-y-6">
        <PanelHeader title="Match threshold" subtitle="The score a job must reach to qualify." />
        <p className="text-small text-text-2">Add a search profile first.</p>
      </section>
    );
  }

  const selected = profiles.find((p) => p.id === selectedId) ?? profiles[0];
  const value = threshold ?? selected.scoreThreshold;

  function save() {
    update.mutate({
      id: selected.id,
      body: { ...profileToInput(selected), scoreThreshold: value },
    });
  }

  return (
    <section data-testid="threshold-settings" className="space-y-6">
      <PanelHeader
        title="Match threshold"
        subtitle="The score a job must reach to qualify, per profile."
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

      <div className="max-w-md">
        <label htmlFor="threshold-range" className="block text-label font-semibold text-text">
          Threshold
        </label>
        <div className="mt-2 flex items-center gap-4">
          <input
            id="threshold-range"
            type="range"
            min={0}
            max={100}
            value={value}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="flex-1 accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
          />
          <span className="w-12 text-right font-mono text-body text-text" data-testid="threshold-value">
            {value}
          </span>
        </div>
      </div>

      <button type="button" onClick={save} disabled={update.isPending} className={primaryClass}>
        {update.isPending ? "Saving…" : "Save threshold"}
      </button>
    </section>
  );
}
