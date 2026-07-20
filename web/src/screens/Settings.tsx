import { useState } from "react";

import { MasterResumePanel } from "../components/MasterResumePanel";
import { SettingsNav, type SectionId } from "../components/SettingsNav";
import { ProfileSettings } from "../components/settings/ProfileSettings";
import { ProviderSettings } from "../components/settings/ProviderSettings";
import { ScheduleSettings } from "../components/settings/ScheduleSettings";
import { ThresholdSettings } from "../components/settings/ThresholdSettings";
import { VoiceSettings } from "../components/settings/VoiceSettings";

// The Settings screen (ui-spec §14.2). W7 makes every CONFIGURATION section live: the
// left rail switches the right pane. All sections read/write the DB-backed settings
// (ADR-031). The screen label and "← Back to search" live in the shared TopBar, which
// App owns along with the view state.

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

export function Settings() {
  const [active, setActive] = useState<SectionId>("voice");

  return (
    <div
      data-testid="settings-screen"
      className="px-6 py-8 lg:grid lg:grid-cols-[264px_minmax(0,1fr)] lg:gap-8"
    >
      <div className="mb-6 lg:mb-0">
        <SettingsNav active={active} onSelect={setActive} />
      </div>

      <div>{panelFor(active)}</div>
    </div>
  );
}
