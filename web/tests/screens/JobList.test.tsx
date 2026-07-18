import { render, screen } from "@testing-library/react";

import { JobList } from "../../src/screens/JobList";
import { useJobs } from "../../src/hooks/useJobs";
import { makeJob } from "../helpers";

jest.mock("../../src/hooks/useJobs");

const mockedUseJobs = useJobs as jest.MockedFunction<typeof useJobs>;

function mockState(state: Partial<ReturnType<typeof useJobs>>) {
  mockedUseJobs.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    refetch: jest.fn(),
    ...state,
  } as unknown as ReturnType<typeof useJobs>);
}

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

  it("renders a card per job when data is present", () => {
    mockState({ data: [makeJob({ id: 1, title: "Alpha" }), makeJob({ id: 2, title: "Beta" })] });
    render(<JobList />);
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
  });
});
