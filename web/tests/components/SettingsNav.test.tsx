import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SettingsNav } from "../../src/components/SettingsNav";
import { api } from "../../src/api/client";
import {
  makeProfile,
  makeResume,
  makeResumeState,
  makeSettings,
  renderWithClient,
} from "../helpers";

jest.mock("../../src/api/client", () => ({
  api: {
    getSettings: jest.fn(),
    listProfiles: jest.fn(),
    getResume: jest.fn(),
  },
}));

const mockedSettings = api.getSettings as jest.MockedFunction<typeof api.getSettings>;
const mockedProfiles = api.listProfiles as jest.MockedFunction<typeof api.listProfiles>;
const mockedResume = api.getResume as jest.MockedFunction<typeof api.getResume>;

const LABELS = [
  "Voice & tone",
  "Search profiles",
  "Evaluator provider",
  "Master resume",
];

beforeEach(() => {
  jest.clearAllMocks();
  mockedSettings.mockResolvedValue(makeSettings({ evaluatorProvider: "anthropic" }));
  mockedProfiles.mockResolvedValue([
    makeProfile({ id: 1, scoreThreshold: 75 }),
    makeProfile({ id: 2, name: "Platform" }),
  ]);
  mockedResume.mockResolvedValue(makeResumeState({ versions: [makeResume({ version: 7 })] }));
});

describe("<SettingsNav>", () => {
  it("renders every section label", () => {
    renderWithClient(<SettingsNav active="voice" onSelect={jest.fn()} />);
    for (const label of LABELS) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
  });

  it("shows the live value for each section", async () => {
    renderWithClient(<SettingsNav active="voice" onSelect={jest.fn()} />);

    // Tone (capitalized), the profile count, the provider label, and the active
    // resume version. (Scheduling is per-profile now — no global schedule rail item.)
    await waitFor(() => expect(screen.getByText("Direct")).toBeInTheDocument());
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Anthropic")).toBeInTheDocument();
    expect(screen.getByText("v7")).toBeInTheDocument();
  });

  it("keeps each button's accessible name the label alone", async () => {
    renderWithClient(<SettingsNav active="voice" onSelect={jest.fn()} />);
    await waitFor(() => expect(screen.getByText("v7")).toBeInTheDocument());
    expect(
      screen.getByRole("button", { name: "Master resume" }),
    ).toBeInTheDocument();
  });

  it("marks the active section and gives it the inset accent bar", () => {
    renderWithClient(<SettingsNav active="profiles" onSelect={jest.fn()} />);

    const activeItem = screen.getByRole("button", { name: "Search profiles" });
    expect(activeItem).toHaveAttribute("aria-current", "page");
    expect(activeItem.className).toContain("shadow-[inset_2px_0_0_var(--accent)]");

    expect(screen.getByRole("button", { name: "Voice & tone" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("calls onSelect with the clicked section", async () => {
    const onSelect = jest.fn();
    renderWithClient(<SettingsNav active="voice" onSelect={onSelect} />);
    await userEvent.click(screen.getByRole("button", { name: "Search profiles" }));
    expect(onSelect).toHaveBeenCalledWith("profiles");
  });

  it("still renders every label when the value queries fail", async () => {
    mockedSettings.mockRejectedValue(new Error("boom"));
    mockedProfiles.mockRejectedValue(new Error("boom"));
    mockedResume.mockRejectedValue(new Error("boom"));

    renderWithClient(<SettingsNav active="voice" onSelect={jest.fn()} />);

    await waitFor(() => expect(mockedSettings).toHaveBeenCalled());
    for (const label of LABELS) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
    // Values degrade to empty rather than blocking the rail.
    expect(screen.queryByText("Anthropic")).not.toBeInTheDocument();
  });
});
