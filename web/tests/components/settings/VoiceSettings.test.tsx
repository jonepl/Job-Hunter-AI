import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { VoiceSettings } from "../../../src/components/settings/VoiceSettings";
import { api } from "../../../src/api/client";
import { makeSettings, renderWithClient } from "../../helpers";

jest.mock("../../../src/api/client", () => ({
  api: { getSettings: jest.fn(), updateSettings: jest.fn() },
}));

const mockedGet = api.getSettings as jest.MockedFunction<typeof api.getSettings>;
const mockedUpdate = api.updateSettings as jest.MockedFunction<typeof api.updateSettings>;

beforeEach(() => {
  jest.clearAllMocks();
  mockedGet.mockResolvedValue(makeSettings());
  mockedUpdate.mockResolvedValue(makeSettings());
});

describe("<VoiceSettings>", () => {
  it("renders a live preview of the composed voice", async () => {
    renderWithClient(<VoiceSettings />);
    const preview = await screen.findByTestId("voice-preview");
    expect(preview).toHaveTextContent(/direct, first person/i);
  });

  it("updates the preview when a different tone card is picked", async () => {
    renderWithClient(<VoiceSettings />);
    await screen.findByTestId("voice-settings");

    await userEvent.click(screen.getByRole("radio", { name: /Warm/ }));
    expect(screen.getByTestId("voice-preview")).toHaveTextContent(/warm/i);
  });

  it("updates the preview when the first-person pill is toggled", async () => {
    renderWithClient(<VoiceSettings />);
    await screen.findByTestId("voice-settings");

    await userEvent.click(screen.getByRole("radio", { name: /Implied/ }));
    expect(screen.getByTestId("voice-preview")).toHaveTextContent(/implied voice/i);
  });

  it("marks the active tone card and leaves the others unchecked", async () => {
    renderWithClient(<VoiceSettings />);
    await screen.findByTestId("voice-settings");

    expect(screen.getByRole("radio", { name: /Direct/ })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("radio", { name: /Warm/ })).toHaveAttribute("aria-checked", "false");
    expect(screen.getByRole("radio", { name: /Formal/ })).toHaveAttribute("aria-checked", "false");
    expect(screen.getByRole("radio", { name: /Bold/ })).toHaveAttribute("aria-checked", "false");
  });

  it("saves the voice", async () => {
    renderWithClient(<VoiceSettings />);
    await screen.findByTestId("voice-settings");

    await userEvent.click(screen.getByRole("button", { name: /Save voice/ }));
    await waitFor(() => expect(mockedUpdate).toHaveBeenCalled());
    expect(mockedUpdate.mock.calls[0][0].voice.tone).toBeDefined();
  });
});
