import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Settings } from "../../src/screens/Settings";

// The panels are exercised in their own tests; stub them here so the Settings shell
// test focuses on the rail + navigation (W7 makes every section live).
jest.mock("../../src/components/settings/VoiceSettings", () => ({
  VoiceSettings: () => <div data-testid="panel-voice" />,
}));
jest.mock("../../src/components/settings/ThresholdSettings", () => ({
  ThresholdSettings: () => <div data-testid="panel-threshold" />,
}));
jest.mock("../../src/components/settings/ScheduleSettings", () => ({
  ScheduleSettings: () => <div data-testid="panel-schedule" />,
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

describe("<Settings>", () => {
  it("renders every CONFIGURATION section as an active rail item", () => {
    render(<Settings onBack={jest.fn()} />);
    for (const label of [
      "Voice & tone",
      "Match threshold",
      "Run schedule",
      "Search profiles",
      "Evaluator provider",
      "Master resume",
    ]) {
      expect(screen.getByRole("button", { name: label })).not.toBeDisabled();
    }
  });

  it("opens on the voice panel and switches panels via the rail", async () => {
    render(<Settings onBack={jest.fn()} />);
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

  it("invokes onBack from the back control", async () => {
    const onBack = jest.fn();
    render(<Settings onBack={onBack} />);
    await userEvent.click(screen.getByRole("button", { name: /Back to search/ }));
    expect(onBack).toHaveBeenCalled();
  });
});
