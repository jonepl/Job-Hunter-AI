import { fireEvent, screen, waitFor } from "@testing-library/react";

import { api } from "../../src/api/client";
import { RunButton } from "../../src/components/RunButton";
import { makeRun, renderWithClient } from "../helpers";

jest.mock("../../src/api/client", () => ({
  api: {
    startRun: jest.fn(),
    getRun: jest.fn(),
    listRuns: jest.fn(),
    listJobs: jest.fn(),
  },
}));

const mockedStart = api.startRun as jest.MockedFunction<typeof api.startRun>;
const mockedGet = api.getRun as jest.MockedFunction<typeof api.getRun>;

beforeEach(() => {
  jest.clearAllMocks();
});

describe("RunButton", () => {
  it("shows the idle label before a run", () => {
    renderWithClient(<RunButton />);
    expect(
      screen.getByRole("button", { name: "Run search now" }),
    ).toBeInTheDocument();
  });

  it("starts a run and reports delivered when it succeeds with qualifying jobs", async () => {
    mockedStart.mockResolvedValue(makeRun({ id: "r1", status: "running" }));
    mockedGet.mockResolvedValue(
      makeRun({
        id: "r1",
        status: "succeeded",
        profilesRun: 2,
        jobsFound: 40,
        qualifying: 5,
        finishedAt: "2026-07-19T09:03:00",
      }),
    );

    renderWithClient(<RunButton />);
    fireEvent.click(screen.getByRole("button", { name: "Run search now" }));

    await waitFor(() =>
      expect(screen.getByText("Search delivered")).toBeInTheDocument(),
    );
    expect(mockedStart).toHaveBeenCalledTimes(1);
    // The summary shows qualifying/found.
    expect(screen.getByText("5/40")).toBeInTheDocument();
  });

  it("reports a zero-results run distinctly from a delivered one", async () => {
    mockedStart.mockResolvedValue(makeRun({ id: "r2", status: "running" }));
    mockedGet.mockResolvedValue(
      makeRun({ id: "r2", status: "succeeded", jobsFound: 12, qualifying: 0 }),
    );

    renderWithClient(<RunButton />);
    fireEvent.click(screen.getByRole("button", { name: "Run search now" }));

    await waitFor(() =>
      expect(screen.getByText("No qualifying results")).toBeInTheDocument(),
    );
  });

  it("surfaces a failed run with its error type, not a raw message", async () => {
    mockedStart.mockResolvedValue(makeRun({ id: "r3", status: "running" }));
    mockedGet.mockResolvedValue(
      makeRun({ id: "r3", status: "failed", error: "RuntimeError" }),
    );

    renderWithClient(<RunButton />);
    fireEvent.click(screen.getByRole("button", { name: "Run search now" }));

    await waitFor(() =>
      expect(screen.getByText("Run failed")).toBeInTheDocument(),
    );
    expect(screen.getByText("RuntimeError")).toBeInTheDocument();
  });

  it("shows a start error without starting a poll", async () => {
    mockedStart.mockRejectedValue(new Error("A run is already in progress."));

    renderWithClient(<RunButton />);
    fireEvent.click(screen.getByRole("button", { name: "Run search now" }));

    await waitFor(() =>
      expect(
        screen.getByText("A run is already in progress."),
      ).toBeInTheDocument(),
    );
    expect(mockedGet).not.toHaveBeenCalled();
  });
});
