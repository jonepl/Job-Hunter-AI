import { useProfiles } from "../hooks/useProfiles";
import { useResume } from "../hooks/useResume";
import { useSettings } from "../hooks/useSettings";

// The Settings left rail. Each item shows its section's live value beside the
// label so the current configuration is readable without opening every panel,
// and the active item carries an inset left accent bar.
//
// The rail is navigation first: it fetches its own values and degrades
// gracefully — a loading or failed query renders the label with an empty value
// rather than blocking or hiding the item. Values are aria-hidden so each
// button's accessible name stays the label alone.

const SECTIONS = [
  { id: "voice", label: "Voice & tone" },
  { id: "threshold", label: "Match threshold" },
  { id: "schedule", label: "Run schedule" },
  { id: "profiles", label: "Search profiles" },
  { id: "provider", label: "Evaluator provider" },
  { id: "resume", label: "Master resume" },
] as const;

export type SectionId = (typeof SECTIONS)[number]["id"];

interface Props {
  active: SectionId;
  onSelect: (id: SectionId) => void;
}

/** Capitalize a stored enum value for display (e.g. "direct" → "Direct"). */
function capitalize(value: string): string {
  return value ? value[0].toUpperCase() + value.slice(1) : "";
}

/** Render the Settings section rail with a live value beside each label. */
export function SettingsNav({ active, onSelect }: Props) {
  const { data: settings } = useSettings();
  const { data: profiles } = useProfiles();
  const { data: resume } = useResume();

  // Threshold is per-profile (ADR-033) — there is no global number, so the rail
  // shows the first/default profile's as a representative value.
  const values: Record<SectionId, string> = {
    voice: settings ? capitalize(settings.voice.tone) : "",
    threshold: profiles?.[0] ? String(profiles[0].scoreThreshold) : "",
    schedule: settings?.scheduleCron ?? "",
    profiles: profiles ? String(profiles.length) : "",
    provider: settings ? (settings.evaluatorProvider === "anthropic" ? "Anthropic" : "OpenAI") : "",
    resume: resume?.active ? `v${resume.active.version}` : "",
  };

  return (
    <nav aria-label="Configuration">
      <h2 className="mb-2 px-2.5 font-mono text-label uppercase tracking-[0.08em] text-text-3">
        Configuration
      </h2>
      <ul className="space-y-1">
        {SECTIONS.map((section) => {
          const isActive = section.id === active;
          return (
            <li key={section.id}>
              <button
                type="button"
                onClick={() => onSelect(section.id)}
                aria-label={section.label}
                aria-current={isActive ? "page" : undefined}
                className={`flex w-full items-center justify-between gap-2 rounded-control px-3 py-[11px] text-left transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 ${
                  isActive
                    ? "bg-accent-soft shadow-[inset_2px_0_0_var(--accent)]"
                    : "hover:bg-surface-2"
                }`}
              >
                <span className="text-control font-semibold text-text">{section.label}</span>
                <span aria-hidden="true" className="font-mono text-label text-text-3">
                  {values[section.id]}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
