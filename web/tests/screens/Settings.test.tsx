import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Settings } from "../../src/screens/Settings";
import { api } from "../../src/api/client";
import { makeProfile, makeResumeState, makeSettings, renderWithRouter } from "../helpers";

// The rail fetches its own live values (SettingsNav has its own test); stub the
// endpoints so this stays a shell test about which panel the rail opens.
jest.mock("../../src/api/client", () => ({
  api: {
    getSettings: jest.fn(),
    listProfiles: jest.fn(),
    getResume: jest.fn(),
  },
}));

// The panels are exercised in their own tests; stub them here so the Settings shell
// test focuses on the rail + navigation (W7 makes every section live).
jest.mock("../../src/components/settings/VoiceSettings", () => ({
  VoiceSettings: () => <div data-testid="panel-voice" />,
}));
jest.mock("../../src/components/settings/ProfileSettings", () => ({
  ProfileSettings: () => <div data-testid="panel-profiles" />,
}));
jest.mock("../../src/components/settings/ProviderSettings", () => ({
  ProviderSettings: () => <div data-testid="panel-provider" />,
}));
jest.mock("../../src/components/MasterResumePanel", () => ({
  MasterResumePanel: () => <div data-testid="master-resume-panel" />,
}));

beforeEach(() => {
  jest.clearAllMocks();
  (api.getSettings as jest.Mock).mockResolvedValue(makeSettings());
  (api.listProfiles as jest.Mock).mockResolvedValue([makeProfile()]);
  (api.getResume as jest.Mock).mockResolvedValue(makeResumeState());
});

describe("<Settings>", () => {
  it("renders every CONFIGURATION section as an active rail item", async () => {
    await renderWithRouter(<Settings />, { initialEntries: ["/settings/voice"] });
    for (const label of [
      "Voice & tone",
      "Search profiles",
      "Evaluator provider",
      "Master resume",
    ]) {
      expect(screen.getByRole("button", { name: label })).not.toBeDisabled();
    }
  });

  it("opens on the voice panel and switches panels via the rail", async () => {
    await renderWithRouter(<Settings />, { initialEntries: ["/settings/voice"] });
    expect(screen.getByTestId("panel-voice")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Search profiles" }));
    expect(screen.getByTestId("panel-profiles")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search profiles" })).toHaveAttribute(
      "aria-current",
      "page",
    );

    await userEvent.click(screen.getByRole("button", { name: "Master resume" }));
    expect(screen.getByTestId("master-resume-panel")).toBeInTheDocument();
  });
});
// "← Back to search" now lives in the shared TopBar (App owns the view state);
// it is covered by TopBar.test.tsx.
