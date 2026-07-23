import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { JobList } from "../../src/screens/JobList";
import { useJobs } from "../../src/hooks/useJobs";
import { useJob, useMarkStatus, useSaved } from "../../src/hooks/useJob";
import { useProfiles } from "../../src/hooks/useProfiles";
import { useRuns } from "../../src/hooks/useRuns";
import {
  useGenerate,
  useGeneration,
  useJobGenerations,
} from "../../src/hooks/useGeneration";
import { SearchViewProvider } from "../../src/lib/searchView";
import { makeJob, makeJobDetail, makeProfile } from "../helpers";

jest.mock("../../src/hooks/useJobs");
jest.mock("../../src/hooks/useJob");
jest.mock("../../src/hooks/useProfiles");
jest.mock("../../src/hooks/useRuns");
jest.mock("../../src/hooks/useGeneration");

const mockedUseJobs = useJobs as jest.MockedFunction<typeof useJobs>;
const mockedUseJob = useJob as jest.MockedFunction<typeof useJob>;
const mockedUseProfiles = useProfiles as jest.MockedFunction<typeof useProfiles>;
const mockedUseRuns = useRuns as jest.MockedFunction<typeof useRuns>;
const mockedUseMarkStatus = useMarkStatus as jest.MockedFunction<typeof useMarkStatus>;
const mockedUseSaved = useSaved as jest.MockedFunction<typeof useSaved>;

function mockState(state: Partial<ReturnType<typeof useJobs>>) {
  mockedUseJobs.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    refetch: jest.fn(),
    ...state,
  } as unknown as ReturnType<typeof useJobs>);
}

function renderList() {
  return render(
    <SearchViewProvider>
      <JobList />
    </SearchViewProvider>,
  );
}

beforeEach(() => {
  // A single profile → the default resolved view is that profile ("Latest run").
  mockedUseProfiles.mockReturnValue({ data: [makeProfile({ id: 1 })] } as unknown as ReturnType<
    typeof useProfiles
  >);
  mockedUseRuns.mockReturnValue({ data: [] } as unknown as ReturnType<typeof useRuns>);
  (useJobGenerations as jest.Mock).mockReturnValue({ data: [] });
  (useGenerate as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false });
  (useGeneration as jest.Mock).mockReturnValue({ data: undefined });
  mockedUseJob.mockReturnValue({
    data: makeJobDetail(),
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useJob>);
  mockedUseMarkStatus.mockReturnValue({
    mutate: jest.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useMarkStatus>);
  mockedUseSaved.mockReturnValue({
    mutate: jest.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useSaved>);
});

describe("<JobList>", () => {
  it("shows a loading state while fetching", () => {
    mockState({ isLoading: true });
    renderList();
    expect(screen.getByText(/Loading jobs/)).toBeInTheDocument();
  });

  it("shows a first-class empty state when there are no jobs", () => {
    mockState({ data: [] });
    renderList();
    expect(screen.getByText("No jobs yet")).toBeInTheDocument();
  });

  it("shows an error state with a retry when the fetch fails", () => {
    mockState({ isError: true });
    renderList();
    expect(screen.getByText(/Couldn’t load your jobs/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Try again/ })).toBeInTheDocument();
  });

  it("renders a card per job and shows the first result's detail by default", () => {
    mockState({ data: [makeJob({ id: 1, title: "Alpha" }), makeJob({ id: 2, title: "Beta" })] });
    renderList();
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
    // No explicit selection yet, but the pane falls back to the first result.
    expect(screen.getByTestId("job-detail")).toBeInTheDocument();
    expect(screen.queryByText(/No job to show yet/)).not.toBeInTheDocument();
  });

  it("shows the empty placeholder only when there are no results", () => {
    mockState({ data: [] });
    renderList();
    expect(screen.getByText(/No job to show yet/)).toBeInTheDocument();
    expect(screen.queryByTestId("job-detail")).not.toBeInTheDocument();
  });

  it("keeps the detail pane open when a card is clicked", async () => {
    mockState({ data: [makeJob({ id: 1, title: "Alpha" })] });
    renderList();

    await userEvent.click(screen.getByTestId("job-card"));
    expect(screen.getByTestId("job-detail")).toBeInTheDocument();
  });

  it("shows every job in the profile view before any filter is applied", () => {
    mockState({
      data: [
        makeJob({ id: 1, title: "Evaluated One", status: "evaluated" }),
        makeJob({ id: 2, title: "In Pipeline", status: "applied" }),
      ],
    });
    renderList();
    expect(screen.getByText("Evaluated One")).toBeInTheDocument();
    expect(screen.getByText("In Pipeline")).toBeInTheDocument();
  });

  it("narrows to a status when its label chip is toggled", async () => {
    mockState({
      data: [
        makeJob({ id: 1, title: "Evaluated One", status: "evaluated" }),
        makeJob({ id: 2, title: "In Pipeline", status: "applied" }),
      ],
    });
    renderList();

    const bar = screen.getByTestId("job-filter-bar");
    await userEvent.click(within(bar).getByRole("button", { name: /Applied/ }));
    expect(screen.getByText("In Pipeline")).toBeInTheDocument();
    expect(screen.queryByText("Evaluated One")).not.toBeInTheDocument();
  });

  it("shows the filtered-empty state when a filter matches nothing", async () => {
    mockState({ data: [makeJob({ id: 1, title: "In Pipeline", status: "applied" })] });
    renderList();

    // No interviewing jobs exist, so filtering to it empties the view.
    const bar = screen.getByTestId("job-filter-bar");
    await userEvent.click(within(bar).getByRole("button", { name: /Interviewing/ }));
    expect(screen.getByTestId("filtered-empty")).toBeInTheDocument();
    expect(screen.queryByText("No jobs yet")).not.toBeInTheDocument();
    expect(screen.getByTestId("job-filter-bar")).toBeInTheDocument();
  });
});
