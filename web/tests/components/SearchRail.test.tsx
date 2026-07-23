import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SearchRail } from "../../src/components/SearchRail";
import { api } from "../../src/api/client";
import { SearchViewProvider } from "../../src/lib/searchView";
import { makeJob, makeProfile, makeRun, renderWithClient } from "../helpers";

jest.mock("../../src/api/client", () => ({
  api: { listJobs: jest.fn(), listProfiles: jest.fn(), listRuns: jest.fn() },
}));

const mockedJobs = api.listJobs as jest.MockedFunction<typeof api.listJobs>;
const mockedProfiles = api.listProfiles as jest.MockedFunction<typeof api.listProfiles>;
const mockedRuns = api.listRuns as jest.MockedFunction<typeof api.listRuns>;

function renderRail() {
  return renderWithClient(
    <SearchViewProvider>
      <SearchRail onNewProfile={jest.fn()} />
    </SearchViewProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  mockedJobs.mockResolvedValue([
    makeJob({ id: 1, status: "applied" }),
    makeJob({ id: 2, status: "interviewing" }),
    makeJob({ id: 3, status: "evaluated" }), // not tracked
  ]);
  mockedProfiles.mockResolvedValue([
    makeProfile({ id: 1, name: "Backend", location: "Remote", scoreThreshold: 75 }),
    makeProfile({ id: 2, name: "Platform" }),
  ]);
  mockedRuns.mockResolvedValue([
    makeRun({ id: "r1", status: "succeeded", qualifying: 3, jobsFound: 10 }),
    makeRun({ id: "r0", status: "failed", error: "TimeoutError" }),
  ]);
});

describe("<SearchRail>", () => {
  it("renders the three rail sections", async () => {
    renderRail();
    expect(screen.getByRole("navigation", { name: "Search navigation" })).toBeInTheDocument();
    expect(screen.getByText("Tracked")).toBeInTheDocument();
    expect(screen.getByText("Search profiles")).toBeInTheDocument();
    expect(screen.getByText("Run history")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Backend" })).toBeInTheDocument(),
    );
  });

  it("counts only the in-flight jobs on the Tracked row", async () => {
    renderRail();
    const tracked = screen.getByRole("button", { name: "All in flight" });
    await waitFor(() => expect(tracked).toHaveTextContent("2"));
  });

  it("marks the resolved profile current with the inset accent bar", async () => {
    renderRail();
    const backend = await screen.findByRole("button", { name: "Backend" });
    expect(backend).toHaveAttribute("aria-current", "page");
    expect(backend.className).toContain("shadow-[inset_2px_0_0_var(--accent)]");
  });

  it("selects a different profile on click", async () => {
    renderRail();
    const platform = await screen.findByRole("button", { name: "Platform" });
    await userEvent.click(platform);
    expect(platform).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: "Backend" })).not.toHaveAttribute("aria-current");
  });

  it("shows the global run history newest-first with a Latest tag", async () => {
    renderRail();
    const history = await screen.findByTestId("run-history");
    expect(history).toHaveTextContent("Latest");
    expect(history).toHaveTextContent("3 matches · delivered");
    expect(history).toHaveTextContent("Failed · TimeoutError");
  });

  it("still renders every section when the queries fail", async () => {
    mockedJobs.mockRejectedValue(new Error("boom"));
    mockedProfiles.mockRejectedValue(new Error("boom"));
    mockedRuns.mockRejectedValue(new Error("boom"));

    renderRail();
    await waitFor(() => expect(mockedProfiles).toHaveBeenCalled());
    expect(screen.getByText("Tracked")).toBeInTheDocument();
    expect(screen.getByText("Search profiles")).toBeInTheDocument();
    expect(screen.getByText("Run history")).toBeInTheDocument();
    expect(screen.getByText("No profiles yet.")).toBeInTheDocument();
    expect(screen.getByText("No runs yet.")).toBeInTheDocument();
  });
});
