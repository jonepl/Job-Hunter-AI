import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ProfileSettings } from "../../../src/components/settings/ProfileSettings";
import { api } from "../../../src/api/client";
import { makeProfile, makeSettings, renderWithClient } from "../../helpers";

jest.mock("../../../src/api/client", () => ({
  api: {
    listProfiles: jest.fn(),
    createProfile: jest.fn(),
    updateProfile: jest.fn(),
    deleteProfile: jest.fn(),
    getSettings: jest.fn(),
  },
}));

const mockedList = api.listProfiles as jest.MockedFunction<typeof api.listProfiles>;
const mockedCreate = api.createProfile as jest.MockedFunction<typeof api.createProfile>;
const mockedUpdate = api.updateProfile as jest.MockedFunction<typeof api.updateProfile>;
const mockedDelete = api.deleteProfile as jest.MockedFunction<typeof api.deleteProfile>;
const mockedGetSettings = api.getSettings as jest.MockedFunction<typeof api.getSettings>;

beforeEach(() => {
  jest.clearAllMocks();
  mockedList.mockResolvedValue([
    makeProfile({ id: 1, name: "Backend" }),
    makeProfile({ id: 2, name: "Frontend" }),
  ]);
  mockedCreate.mockResolvedValue(makeProfile({ id: 3, name: "New" }));
  mockedUpdate.mockResolvedValue(makeProfile({ id: 1, name: "Backend" }));
  mockedDelete.mockResolvedValue(undefined);
  mockedGetSettings.mockResolvedValue(makeSettings());
});

describe("<ProfileSettings>", () => {
  it("lists the stored profiles", async () => {
    renderWithClient(<ProfileSettings />);
    const list = await screen.findByTestId("profile-list");
    expect(list).toHaveTextContent("Backend");
    expect(list).toHaveTextContent("Frontend");
  });

  it("creates a profile through the editor", async () => {
    renderWithClient(<ProfileSettings />);
    await screen.findByTestId("profile-list");

    await userEvent.click(screen.getByRole("button", { name: "+ New profile" }));
    await userEvent.type(screen.getByLabelText("Query"), "Staff Engineer");
    await userEvent.click(screen.getByRole("button", { name: /Save profile/ }));

    await waitFor(() => expect(mockedCreate).toHaveBeenCalled());
    expect(mockedCreate.mock.calls[0][0].query).toBe("Staff Engineer");
  });

  it("deletes a non-last profile", async () => {
    renderWithClient(<ProfileSettings />);
    await screen.findByTestId("profile-list");

    await userEvent.click(screen.getByRole("button", { name: "Delete Backend" }));
    await waitFor(() => expect(mockedDelete).toHaveBeenCalledWith(1));
  });

  it("shows Resume + Paused for a disabled profile and Pause for an enabled one", async () => {
    mockedList.mockResolvedValue([
      makeProfile({ id: 1, name: "Backend", enabled: true }),
      makeProfile({ id: 2, name: "Frontend", enabled: false }),
    ]);
    renderWithClient(<ProfileSettings />);
    await screen.findByTestId("profile-list");

    expect(screen.getByRole("button", { name: "Pause Backend" })).toBeInTheDocument();
    const paused = screen.getByRole("button", { name: "Resume Frontend" });
    expect(paused).toBeInTheDocument();
    // The paused row's meta reads "Paused".
    const frontendRow = paused.closest("li")!;
    expect(within(frontendRow).getByText("Paused")).toBeInTheDocument();
  });

  it("pausing calls updateProfile with enabled:false and the other fields intact", async () => {
    mockedList.mockResolvedValue([
      makeProfile({ id: 1, name: "Backend", query: "SWE", enabled: true }),
      makeProfile({ id: 2, name: "Frontend" }),
    ]);
    renderWithClient(<ProfileSettings />);
    await screen.findByTestId("profile-list");

    await userEvent.click(screen.getByRole("button", { name: "Pause Backend" }));

    await waitFor(() => expect(mockedUpdate).toHaveBeenCalled());
    expect(mockedUpdate).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ enabled: false, name: "Backend", query: "SWE" }),
    );
  });

  it("renders the platforms derived from activeScrapers", async () => {
    mockedList.mockResolvedValue([
      makeProfile({ id: 1, name: "Backend", activeScrapers: ["linkedin", "indeed"] }),
    ]);
    renderWithClient(<ProfileSettings />);
    const list = await screen.findByTestId("profile-list");

    expect(within(list).getByText("LinkedIn · Indeed")).toBeInTheDocument();
  });

  it("renders 'running now' for a profile whose last run is in progress", async () => {
    mockedList.mockResolvedValue([
      makeProfile({ id: 1, name: "Backend", enabled: true, lastRunStatus: "running" }),
    ]);
    renderWithClient(<ProfileSettings />);
    const list = await screen.findByTestId("profile-list");

    expect(within(list).getByText("running now")).toBeInTheDocument();
  });

  it("saves the edited threshold from the number input", async () => {
    mockedList.mockResolvedValue([makeProfile({ id: 1, name: "Backend", scoreThreshold: 70 })]);
    renderWithClient(<ProfileSettings />);
    await screen.findByTestId("profile-list");

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    const box = await screen.findByLabelText("Score threshold value");
    await userEvent.clear(box);
    await userEvent.type(box, "85");
    await userEvent.click(screen.getByRole("button", { name: /Save profile/ }));

    await waitFor(() => expect(mockedUpdate).toHaveBeenCalled());
    expect(mockedUpdate).toHaveBeenCalledWith(1, expect.objectContaining({ scoreThreshold: 85 }));
  });

  it("renders the near-miss band from the backend band width", async () => {
    mockedList.mockResolvedValue([makeProfile({ id: 1, name: "Backend", scoreThreshold: 70 })]);
    mockedGetSettings.mockResolvedValue(makeSettings({ nearMissBand: 15 }));
    renderWithClient(<ProfileSettings />);
    await screen.findByTestId("profile-list");

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    // Profile threshold 70, band 15 → floor 55, top threshold − 1 = 69.
    expect(await screen.findByText("55–69")).toBeInTheDocument();
  });
});
