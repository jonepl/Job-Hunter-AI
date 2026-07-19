import { useState } from "react";

import { MasterResumePanel } from "../components/MasterResumePanel";
import { ProfileSettings } from "../components/settings/ProfileSettings";
import { ProviderSettings } from "../components/settings/ProviderSettings";
import { ScheduleSettings } from "../components/settings/ScheduleSettings";
import { ThresholdSettings } from "../components/settings/ThresholdSettings";
import { VoiceSettings } from "../components/settings/VoiceSettings";

// The Settings screen (ui-spec §14.2). W7 makes every CONFIGURATION section live: the
// left rail switches the right pane. All sections read/write the DB-backed settings
// (ADR-031); "← Back to search" returns to the job list (App owns the view state).

interface Props {
  onBack: () => void;
}

const SECTIONS = [
  { id: "voice", label: "Voice & tone" },
  { id: "threshold", label: "Match threshold" },
  { id: "schedule", label: "Run schedule" },
  { id: "profiles", label: "Search profiles" },
  { id: "provider", label: "Evaluator provider" },
  { id: "resume", label: "Master resume" },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

function panelFor(id: SectionId) {
  switch (id) {
    case "voice":
      return <VoiceSettings />;
    case "threshold":
      return <ThresholdSettings />;
    case "schedule":
      return <ScheduleSettings />;
    case "profiles":
      return <ProfileSettings />;
    case "provider":
      return <ProviderSettings />;
    case "resume":
      return <MasterResumePanel />;
  }
}

export function Settings({ onBack }: Props) {
  const [active, setActive] = useState<SectionId>("voice");

  return (
    <div data-testid="settings-screen">
      <div className="mb-6 flex items-center gap-4">
        <h1 className="font-mono text-label uppercase tracking-[0.08em] text-text-3">
          Settings
        </h1>
        <button
          type="button"
          onClick={onBack}
          className="text-small text-text-2 transition-colors duration-fast hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          ← Back to search
        </button>
      </div>

      <div className="lg:grid lg:grid-cols-[minmax(0,14rem)_minmax(0,1fr)] lg:gap-8">
        <nav aria-label="Configuration" className="mb-6 lg:mb-0">
          <h2 className="mb-3 font-mono text-label uppercase tracking-[0.05em] text-text-3">
            Configuration
          </h2>
          <ul className="space-y-1">
            {SECTIONS.map((section) => {
              const isActive = section.id === active;
              return (
                <li key={section.id}>
                  <button
                    type="button"
                    onClick={() => setActive(section.id)}
                    aria-current={isActive ? "page" : undefined}
                    className={`w-full rounded-control px-3 py-2 text-left text-control transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 ${
                      isActive ? "bg-accent-soft text-accent" : "text-text-2 hover:text-text"
                    }`}
                  >
                    {section.label}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        <div>{panelFor(active)}</div>
      </div>
    </div>
  );
}
