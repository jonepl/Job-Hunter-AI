import { useState } from "react";

import { useSettings, useUpdateSettings } from "../../hooks/useSettings";
import { settingsToUpdate, voiceDiffersFromEnv } from "../../lib/settings";
import { DiffBadge } from "./DiffBadge";
import {
  Field,
  PanelError,
  PanelHeader,
  PanelStatus,
  inputClass,
  primaryClass,
  selectClass,
} from "./shared";

// Voice & tone section (ADR-030): the global cover-letter voice descriptor — a tone
// preset, a first-person toggle, and free-text style notes — with a live preview of
// the composed instruction (no LLM; just echoes what the model will be told).

const TONES = ["direct", "warm", "formal", "bold"] as const;

function previewLine(tone: string, person: string, notes: string): string {
  const pov = person === "first_person" ? "first person" : "an implied voice";
  const base = `Write in a ${tone}, ${pov} tone.`;
  return notes.trim() ? `${base} ${notes.trim()}` : base;
}

export function VoiceSettings() {
  const { data: settings, isLoading, isError } = useSettings();
  const update = useUpdateSettings();
  const [tone, setTone] = useState<string | null>(null);
  const [person, setPerson] = useState<string | null>(null);
  const [notes, setNotes] = useState<string | null>(null);

  if (isLoading) return <PanelStatus>Loading settings…</PanelStatus>;
  if (isError || !settings) return <PanelError />;

  const toneValue = tone ?? settings.voice.tone;
  const personValue = person ?? settings.voice.person;
  const notesValue = notes ?? settings.voice.styleNotes;

  function save() {
    update.mutate({
      ...settingsToUpdate(settings!),
      voice: {
        tone: toneValue as "direct" | "warm" | "formal" | "bold",
        person: personValue as "first_person" | "implied",
        styleNotes: notesValue,
      },
    });
  }

  return (
    <section data-testid="voice-settings" className="space-y-6">
      <div className="flex items-center gap-2">
        <PanelHeader
          title="Voice & tone"
          subtitle="How generated cover letters should sound."
        />
        <DiffBadge show={voiceDiffersFromEnv(settings)} />
      </div>

      <Field label="Tone" htmlFor="tone">
        <select id="tone" value={toneValue} onChange={(e) => setTone(e.target.value)} className={selectClass}>
          {TONES.map((t) => (
            <option key={t} value={t}>
              {t[0].toUpperCase() + t.slice(1)}
            </option>
          ))}
        </select>
      </Field>

      <Field label="Point of view" htmlFor="person">
        <select id="person" value={personValue} onChange={(e) => setPerson(e.target.value)} className={selectClass}>
          <option value="first_person">First person (“I”)</option>
          <option value="implied">Implied</option>
        </select>
      </Field>

      <Field label="Style notes" htmlFor="notes" hint="Free-text instructions the model follows.">
        <textarea
          id="notes"
          value={notesValue}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="e.g. Keep sentences short. Lead with outcomes."
          className={inputClass}
        />
      </Field>

      <div>
        <h3 className="font-mono text-label uppercase tracking-[0.05em] text-text-3">Preview</h3>
        <p className="mt-2 rounded-card border border-border bg-surface-2 p-4 text-small text-text-2" data-testid="voice-preview">
          {previewLine(toneValue, personValue, notesValue)}
        </p>
      </div>

      <button type="button" onClick={save} disabled={update.isPending} className={primaryClass}>
        {update.isPending ? "Saving…" : "Save voice"}
      </button>
    </section>
  );
}
