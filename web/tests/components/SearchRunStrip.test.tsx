import { screen, waitFor } from "@testing-library/react";

import { SearchRunStrip } from "../../src/components/SearchTopBar";
import { api } from "../../src/api/client";
import { makeProfile, makeRun, renderWithClient } from "../helpers";

jest.mock("../../src/api/client", () => ({
  api: { listRuns: jest.fn(), listProfiles: jest.fn() },
}));

const mockedRuns = api.listRuns as jest.MockedFunction<typeof api.listRuns>;
const mockedProfiles = api.listProfiles as jest.MockedFunction<typeof api.listProfiles>;

beforeEach(() => {
  jest.clearAllMocks();
});

describe("<SearchRunStrip>", () => {
  it("shows 'Running N profiles' while a global batch is live", async () => {
    mockedRuns.mockResolvedValue([makeRun({ status: "running", profileId: null })]);
    mockedProfiles.mockResolvedValue([
      makeProfile({ id: 1, enabled: true }),
      makeProfile({ id: 2, enabled: true }),
      makeProfile({ id: 3, enabled: false }), // paused → not counted
    ]);

    renderWithClient(<SearchRunStrip />);
    await waitFor(() =>
      expect(screen.getByTestId("run-strip")).toHaveTextContent("Running 2 profiles…"),
    );
  });

  it("shows a singular count for a per-profile run", async () => {
    mockedRuns.mockResolvedValue([makeRun({ status: "running", profileId: 5 })]);
    mockedProfiles.mockResolvedValue([makeProfile({ id: 5 })]);

    renderWithClient(<SearchRunStrip />);
    await waitFor(() =>
      expect(screen.getByTestId("run-strip")).toHaveTextContent("Running 1 profile…"),
    );
  });

  it("shows the soonest next scheduled run when idle", async () => {
    mockedRuns.mockResolvedValue([makeRun({ status: "succeeded" })]);
    mockedProfiles.mockResolvedValue([
      makeProfile({ id: 1, scheduleEnabled: true, nextRunAt: "2099-01-02T08:00:00" }),
      makeProfile({ id: 2, scheduleEnabled: true, nextRunAt: "2099-01-01T08:00:00" }),
    ]);

    renderWithClient(<SearchRunStrip />);
    await waitFor(() =>
      expect(screen.getByTestId("run-strip")).toHaveTextContent(/Next scheduled run/),
    );
  });

  it("renders nothing when nothing is running and nothing is scheduled", async () => {
    mockedRuns.mockResolvedValue([makeRun({ status: "succeeded" })]);
    mockedProfiles.mockResolvedValue([makeProfile({ id: 1, nextRunAt: null })]);

    renderWithClient(<SearchRunStrip />);
    await waitFor(() => expect(mockedProfiles).toHaveBeenCalled());
    expect(screen.queryByTestId("run-strip")).not.toBeInTheDocument();
  });
});
