import { useState } from "react";

import { useSettings, useUpdateSettings } from "../../hooks/useSettings";
import { settingsToUpdate, voiceDiffersFromEnv } from "../../lib/settings";
import { DiffBadge } from "./DiffBadge";
import { PanelError, PanelHeader, PanelStatus, inputClass, primaryClass } from "./shared";

// Voice & tone section (ADR-030): the global cover-letter voice descriptor — a tone
// preset, a first-person toggle, and free-text style notes — with a live preview of
// the composed instruction (no LLM; just echoes what the model will be told).

// Tone presets, each with the one-line description the picker cards show.
const TONES: { key: "direct" | "warm" | "formal" | "bold"; label: string; desc: string }[] = [
  { key: "direct", label: "Direct", desc: "Short, factual, outcome-led" },
  { key: "warm", label: "Warm", desc: "Personable but professional" },
  { key: "formal", label: "Formal", desc: "Traditional, conservative fields" },
  { key: "bold", label: "Bold", desc: "Confident, startup-flavored" },
];

// First-person voice options, rendered as the two-pill toggle.
const PERSONS: { value: "first_person" | "implied"; label: string }[] = [
  { value: "first_person", label: 'First person ("I led…")' },
  { value: "implied", label: 'Implied ("Led…")' },
];

// 13px/600 sub-label above each control group (no matching token; design.md §form fields).
const subLabelClass = "block text-[13px] font-semibold text-text";

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

      {/* Tone — four selectable cards, each with a description. */}
      <div className="space-y-2.5">
        <span className={subLabelClass}>Tone</span>
        <div role="radiogroup" aria-label="Tone" className="flex max-w-[640px] flex-wrap gap-2.5">
          {TONES.map((t) => {
            const active = t.key === toneValue;
            return (
              <button
                key={t.key}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setTone(t.key)}
                className={
                  "w-[150px] rounded-card border p-3.5 text-left transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 " +
                  (active
                    ? "border-accent bg-accent-soft"
                    : "border-border bg-surface hover:border-border-strong")
                }
              >
                <span className="text-control font-semibold text-text">{t.label}</span>
                <span className="mt-[3px] block text-small text-text-2">{t.desc}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* First-person voice — two pill toggles. */}
      <div className="space-y-2.5">
        <span className={subLabelClass}>First-person voice</span>
        <div role="radiogroup" aria-label="First-person voice" className="flex gap-2">
          {PERSONS.map((p) => {
            const active = p.value === personValue;
            return (
              <button
                key={p.value}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setPerson(p.value)}
                className={
                  "rounded-pill border px-[15px] py-[9px] text-small font-semibold transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 " +
                  (active
                    ? "border-accent bg-accent-soft text-accent"
                    : "border-border bg-surface text-text-2 hover:border-border-strong")
                }
              >
                {p.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Style notes — free-text instructions the generator follows. */}
      <div className="space-y-2.5">
        <label htmlFor="notes" className={subLabelClass}>
          Style notes for the generator
        </label>
        <textarea
          id="notes"
          value={notesValue}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="e.g. Keep sentences short. Lead with outcomes."
          className={inputClass}
        />
      </div>

      {/* Preview — the live composed instruction, in the design's bordered card. */}
      <div className="max-w-[640px] rounded-card border border-border bg-surface p-4">
        <div className="text-[13px] font-semibold text-text">Preview with current settings</div>
        <p className="mt-1 text-small italic text-text-2" data-testid="voice-preview">
          “{previewLine(toneValue, personValue, notesValue)}”
        </p>
      </div>

      <button type="button" onClick={save} disabled={update.isPending} className={primaryClass}>
        {update.isPending ? "Saving…" : "Save voice"}
      </button>
    </section>
  );
}
