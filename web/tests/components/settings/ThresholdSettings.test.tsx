import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ThresholdSettings } from "../../../src/components/settings/ThresholdSettings";
import { api } from "../../../src/api/client";
import { makeProfile, makeSettings, renderWithClient } from "../../helpers";

jest.mock("../../../src/api/client", () => ({
  api: { listProfiles: jest.fn(), updateProfile: jest.fn(), getSettings: jest.fn() },
}));

const mockedList = api.listProfiles as jest.MockedFunction<typeof api.listProfiles>;
const mockedUpdate = api.updateProfile as jest.MockedFunction<typeof api.updateProfile>;
const mockedGet = api.getSettings as jest.MockedFunction<typeof api.getSettings>;

beforeEach(() => {
  jest.clearAllMocks();
  mockedList.mockResolvedValue([makeProfile({ id: 3, scoreThreshold: 70 })]);
  mockedUpdate.mockResolvedValue(makeProfile({ id: 3, scoreThreshold: 85 }));
  mockedGet.mockResolvedValue(makeSettings());
});

describe("<ThresholdSettings>", () => {
  it("writes the selected profile's threshold", async () => {
    renderWithClient(<ThresholdSettings />);
    await screen.findByTestId("threshold-settings");

    fireEvent.change(screen.getByLabelText("Threshold"), { target: { value: "85" } });
    expect(screen.getByTestId("threshold-value")).toHaveTextContent("85");

    await userEvent.click(screen.getByRole("button", { name: /Save threshold/ }));
    await waitFor(() => expect(mockedUpdate).toHaveBeenCalled());
    const call = mockedUpdate.mock.calls[0];
    expect(call[0]).toBe(3);
    expect(call[1].scoreThreshold).toBe(85);
  });

  it("renders the near-miss band from the backend band width", async () => {
    mockedGet.mockResolvedValue(makeSettings({ nearMissBand: 15 }));
    renderWithClient(<ThresholdSettings />);
    await screen.findByTestId("threshold-settings");

    // Profile threshold 70, band 15 → floor 55, top threshold − 1 = 69.
    expect(await screen.findByText("55–69")).toBeInTheDocument();
  });

  it("shows the selected profile's name under 'Applies to'", async () => {
    mockedList.mockResolvedValue([makeProfile({ id: 3, name: "Backend", scoreThreshold: 70 })]);
    renderWithClient(<ThresholdSettings />);
    await screen.findByTestId("threshold-settings");

    // "Backend" also appears in the profile <option>, so scope to the stat cell.
    const appliesTo = await screen.findByText("Applies to");
    expect(appliesTo.parentElement).toHaveTextContent("Backend");
  });
});
