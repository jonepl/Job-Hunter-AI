import { useState } from "react";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SearchRail } from "../../src/components/SearchRail";
import { api } from "../../src/api/client";
import { makeJob, makeProfile, makeRun, renderWithRouter } from "../helpers";

jest.mock("../../src/api/client", () => ({
  api: {
    listJobs: jest.fn(),
    listProfiles: jest.fn(),
    listRuns: jest.fn(),
    startRun: jest.fn(),
    getRun: jest.fn(),
  },
}));

const mockedJobs = api.listJobs as jest.MockedFunction<typeof api.listJobs>;
const mockedProfiles = api.listProfiles as jest.MockedFunction<typeof api.listProfiles>;
const mockedRuns = api.listRuns as jest.MockedFunction<typeof api.listRuns>;
const mockedStartRun = api.startRun as jest.MockedFunction<typeof api.startRun>;

/** A stateful harness so multi-select changes propagate the way JobList wires them. */
function Harness({
  initialSelected = new Set<number>(),
  onConfigure = jest.fn(),
}: {
  initialSelected?: Set<number>;
  onConfigure?: (profile: never) => void;
}) {
  const [selected, setSelected] = useState(initialSelected);
  return (
    <SearchRail
      onNewProfile={jest.fn()}
      onConfigure={onConfigure as never}
      selectedIds={selected}
      onSelectionChange={setSelected}
    />
  );
}

function renderRail(props: Parameters<typeof Harness>[0] = {}) {
  return renderWithRouter(<Harness {...props} />);
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
  // Two runs for profile 1 — one scheduled, one ad-hoc; the newest is delivered.
  mockedRuns.mockResolvedValue([
    makeRun({
      id: "r1",
      status: "succeeded",
      qualifying: 3,
      jobsFound: 10,
      profileId: 1,
      trigger: "scheduled",
    }),
    makeRun({ id: "r0", status: "failed", error: "TimeoutError", profileId: 1, trigger: "web" }),
  ]);
});

describe("<SearchRail>", () => {
  it("renders the three rail sections", async () => {
    await renderRail();
    expect(screen.getByRole("navigation", { name: "Search navigation" })).toBeInTheDocument();
    expect(screen.getByText("Tracked")).toBeInTheDocument();
    expect(screen.getByText("Search profiles")).toBeInTheDocument();
    expect(screen.getByText("Run history")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Backend" })).toBeInTheDocument(),
    );
  });

  it("counts only the in-flight jobs on the Tracked row", async () => {
    await renderRail();
    const tracked = screen.getByRole("button", { name: "All in flight" });
    await waitFor(() => expect(tracked).toHaveTextContent("2"));
  });

  it("marks the resolved profile current with the inset accent bar", async () => {
    await renderRail();
    const backend = await screen.findByRole("button", { name: "Backend" });
    expect(backend).toHaveAttribute("aria-current", "page");
    // The active surface (accent bar) is the row container that holds the checkbox,
    // the select button, and the ⚙ gear together.
    expect(backend.parentElement?.className).toContain("shadow-[inset_2px_0_0_var(--accent)]");
  });

  it("selects a different profile on click", async () => {
    await renderRail();
    const platform = await screen.findByRole("button", { name: "Platform" });
    await userEvent.click(platform);
    expect(platform).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: "Backend" })).not.toHaveAttribute("aria-current");
  });

  it("shows a per-profile status line from the latest run", async () => {
    await renderRail();
    // Backend's newest run delivered 3 matches; Platform has no per-profile run.
    await screen.findByRole("button", { name: "Backend" });
    expect(screen.getByText("Delivered · 3 matches")).toBeInTheDocument();
    expect(screen.getByText("Not scheduled")).toBeInTheDocument();
  });

  it("shows the selected profile's run history with Ad-hoc/Scheduled badges", async () => {
    await renderRail();
    const history = await screen.findByTestId("run-history");
    expect(history).toHaveTextContent("Latest");
    expect(history).toHaveTextContent("3 matches · delivered");
    expect(history).toHaveTextContent("Failed · TimeoutError");
    expect(history).toHaveTextContent("Scheduled");
    expect(history).toHaveTextContent("Ad-hoc");
  });

  it("selects and clears every profile with the Select-all toggle", async () => {
    await renderRail();
    await screen.findByRole("button", { name: "Backend" });

    await userEvent.click(screen.getByRole("button", { name: "Select all" }));
    const boxes = screen.getAllByRole("checkbox");
    expect(boxes.every((b) => (b as HTMLInputElement).checked)).toBe(true);

    await userEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(screen.getAllByRole("checkbox").every((b) => (b as HTMLInputElement).checked)).toBe(
      false,
    );
  });

  it("labels the sticky run button with the selection count and disables it when empty", async () => {
    await renderRail();
    await screen.findByRole("button", { name: "Backend" });

    // Empty selection → disabled zero-count button.
    const zero = screen.getByRole("button", { name: "Run 0 selected now" });
    expect(zero).toBeDisabled();

    await userEvent.click(screen.getByLabelText("Select Backend"));
    expect(screen.getByRole("button", { name: "Run 1 selected now" })).toBeEnabled();
  });

  it("runs the selected profiles sequentially under the single-flight guard", async () => {
    // Each run resolves already-terminal so the poll loop returns without waiting.
    mockedStartRun.mockImplementation(async (id) =>
      makeRun({ id: `run-${id}`, status: "succeeded", profileId: id }),
    );
    await renderRail({ initialSelected: new Set([1, 2]) });
    await screen.findByRole("button", { name: "Backend" });

    await userEvent.click(screen.getByRole("button", { name: "Run 2 selected now" }));

    await waitFor(() => expect(mockedStartRun).toHaveBeenCalledTimes(2));
    expect(mockedStartRun.mock.calls.map((c) => c[0])).toEqual([1, 2]);
  });

  it("opens the configure modal for a profile via its gear", async () => {
    const onConfigure = jest.fn();
    await renderRail({ onConfigure });
    await userEvent.click(await screen.findByLabelText("Configure Backend"));
    expect(onConfigure).toHaveBeenCalledWith(expect.objectContaining({ id: 1, name: "Backend" }));
  });

  it("degrades every section when the queries fail", async () => {
    mockedJobs.mockRejectedValue(new Error("boom"));
    mockedProfiles.mockRejectedValue(new Error("boom"));
    mockedRuns.mockRejectedValue(new Error("boom"));

    await renderRail();
    await waitFor(() => expect(mockedProfiles).toHaveBeenCalled());
    expect(screen.getByText("Tracked")).toBeInTheDocument();
    expect(screen.getByText("Search profiles")).toBeInTheDocument();
    expect(screen.getByText("Run history")).toBeInTheDocument();
    expect(screen.getByText("No profiles yet.")).toBeInTheDocument();
    // No profile can resolve, so the history invites picking one.
    expect(screen.getByText("Select a profile to see its runs.")).toBeInTheDocument();
  });
});
