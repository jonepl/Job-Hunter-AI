import { useNavigate, useParams } from "@tanstack/react-router";

import { MasterResumePanel } from "../components/MasterResumePanel";
import { SettingsNav, isSectionId, type SectionId } from "../components/SettingsNav";
import { ProfileSettings } from "../components/settings/ProfileSettings";
import { ProviderSettings } from "../components/settings/ProviderSettings";
import { ScheduleSettings } from "../components/settings/ScheduleSettings";
import { VoiceSettings } from "../components/settings/VoiceSettings";

// The Settings screen (ui-spec §14.2). W7 makes every CONFIGURATION section live: the
// left rail switches the right pane. The active section lives in the URL path
// (/settings/<section>) so it survives a reload and is deep-linkable — the rail just
// navigates. All sections read/write the DB-backed settings (ADR-031). The screen
// label and "← Back to search" live in the shared TopBar, which the router root owns.

function panelFor(id: SectionId) {
  switch (id) {
    case "voice":
      return <VoiceSettings />;
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
  const navigate = useNavigate();
  const params = useParams({ strict: false }) as { section?: string };
  // The route guards the segment (invalid -> /settings/voice), but default here too
  // so the screen is self-sufficient when rendered outside the real route (tests).
  const active: SectionId = isSectionId(params.section) ? params.section : "voice";

  return (
    <div
      data-testid="settings-screen"
      className="px-6 py-8 lg:grid lg:grid-cols-[264px_minmax(0,1fr)] lg:gap-8"
    >
      <div className="mb-6 lg:mb-0">
        <SettingsNav
          active={active}
          onSelect={(section) => void navigate({ to: "/settings/$section", params: { section } })}
        />
      </div>

      <div>{panelFor(active)}</div>
    </div>
  );
}
