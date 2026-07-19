import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { JobList } from "../../src/screens/JobList";
import { useJobs } from "../../src/hooks/useJobs";
import { useJob, useMarkStatus, useSaved } from "../../src/hooks/useJob";
import { makeJob, makeJobDetail } from "../helpers";

jest.mock("../../src/hooks/useJobs");
jest.mock("../../src/hooks/useJob");

const mockedUseJobs = useJobs as jest.MockedFunction<typeof useJobs>;
const mockedUseJob = useJob as jest.MockedFunction<typeof useJob>;
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

beforeEach(() => {
  // JobDetail (mounted on selection) leans on these; give them inert defaults.
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
    render(<JobList />);
    expect(screen.getByText(/Loading jobs/)).toBeInTheDocument();
  });

  it("shows a first-class empty state when there are no jobs", () => {
    mockState({ data: [] });
    render(<JobList />);
    expect(screen.getByText("No jobs yet")).toBeInTheDocument();
  });

  it("shows an error state with a retry when the fetch fails", () => {
    mockState({ isError: true });
    render(<JobList />);
    expect(screen.getByText(/Couldn’t load your jobs/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Try again/ })).toBeInTheDocument();
  });

  it("renders a card per job with a detail placeholder until one is selected", () => {
    mockState({ data: [makeJob({ id: 1, title: "Alpha" }), makeJob({ id: 2, title: "Beta" })] });
    render(<JobList />);
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
    expect(screen.getByText(/Select a job to see its details/)).toBeInTheDocument();
    expect(screen.queryByTestId("job-detail")).not.toBeInTheDocument();
  });

  it("opens the detail pane when a card is clicked", async () => {
    mockState({ data: [makeJob({ id: 1, title: "Alpha" })] });
    render(<JobList />);

    await userEvent.click(screen.getByTestId("job-card"));
    expect(screen.getByTestId("job-detail")).toBeInTheDocument();
  });

  it("opens on the triage view, hiding non-triage jobs", () => {
    mockState({
      data: [
        makeJob({ id: 1, title: "Triage One", status: "evaluated" }),
        makeJob({ id: 2, title: "In Pipeline", status: "applied" }),
      ],
    });
    render(<JobList />);
    expect(screen.getByText("Triage One")).toBeInTheDocument();
    expect(screen.queryByText("In Pipeline")).not.toBeInTheDocument();
  });

  it("switches to the pipeline view on demand", async () => {
    mockState({
      data: [
        makeJob({ id: 1, title: "Triage One", status: "evaluated" }),
        makeJob({ id: 2, title: "In Pipeline", status: "applied" }),
      ],
    });
    render(<JobList />);

    await userEvent.click(screen.getByRole("button", { name: /Pipeline/ }));
    expect(screen.getByText("In Pipeline")).toBeInTheDocument();
    expect(screen.queryByText("Triage One")).not.toBeInTheDocument();
  });

  it("shows every job under the All view", async () => {
    mockState({
      data: [
        makeJob({ id: 1, title: "Triage One", status: "evaluated" }),
        makeJob({ id: 2, title: "In Pipeline", status: "applied" }),
      ],
    });
    render(<JobList />);

    await userEvent.click(screen.getByRole("button", { name: /All/ }));
    expect(screen.getByText("Triage One")).toBeInTheDocument();
    expect(screen.getByText("In Pipeline")).toBeInTheDocument();
  });

  it("shows a filtered-empty state when the active view has no jobs", () => {
    mockState({ data: [makeJob({ id: 1, title: "In Pipeline", status: "applied" })] });
    render(<JobList />);
    // Default triage view is empty even though a job exists.
    expect(screen.getByText(/Nothing left to triage/)).toBeInTheDocument();
    // The global empty copy must not appear.
    expect(screen.queryByText("No jobs yet")).not.toBeInTheDocument();
    // The filter bar stays visible so the user can switch out.
    expect(screen.getByTestId("job-filter-bar")).toBeInTheDocument();
  });
});
