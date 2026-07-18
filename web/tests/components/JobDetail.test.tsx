import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { JobDetail } from "../../src/components/JobDetail";
import { useJob, useMarkStatus, useSaved } from "../../src/hooks/useJob";
import { makeJobDetail } from "../helpers";

jest.mock("../../src/hooks/useJob");

const mockedUseJob = useJob as jest.MockedFunction<typeof useJob>;
const mockedUseMarkStatus = useMarkStatus as jest.MockedFunction<typeof useMarkStatus>;
const mockedUseSaved = useSaved as jest.MockedFunction<typeof useSaved>;

const markMutate = jest.fn();
const savedMutate = jest.fn();

function mockJobState(state: Partial<ReturnType<typeof useJob>>) {
  mockedUseJob.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    ...state,
  } as unknown as ReturnType<typeof useJob>);
}

beforeEach(() => {
  markMutate.mockReset();
  savedMutate.mockReset();
  mockedUseMarkStatus.mockReturnValue({
    mutate: markMutate,
    isPending: false,
  } as unknown as ReturnType<typeof useMarkStatus>);
  mockedUseSaved.mockReturnValue({
    mutate: savedMutate,
    isPending: false,
  } as unknown as ReturnType<typeof useSaved>);
});

describe("<JobDetail>", () => {
  it("shows a loading state", () => {
    mockJobState({ isLoading: true });
    render(<JobDetail jobId={1} />);
    expect(screen.getByText(/Loading job/)).toBeInTheDocument();
  });

  it("shows an error state", () => {
    mockJobState({ isError: true });
    render(<JobDetail jobId={1} />);
    expect(screen.getByText(/Couldn’t load this job/)).toBeInTheDocument();
  });

  it("renders the fan-out: breakdown, skills, description, timeline, generation stub", () => {
    mockJobState({ data: makeJobDetail() });
    render(<JobDetail jobId={1} />);

    expect(screen.getByRole("heading", { name: "Senior Software Engineer" })).toBeInTheDocument();
    expect(screen.getByTestId("score-breakdown").querySelectorAll("li")).toHaveLength(9);
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("Kubernetes")).toHaveAttribute("data-skill", "miss");
    expect(screen.getByText(/Own end-to-end design/)).toBeInTheDocument();
    expect(screen.getByTestId("status-timeline")).toHaveTextContent("Created as Evaluated");
    expect(screen.getAllByTestId("generation-chip")).toHaveLength(2);
    expect(screen.getByRole("link", { name: /View original posting/ })).toHaveAttribute(
      "href",
      "https://example.com/jobs/1",
    );
  });

  it("marks a status through the mutation hook", async () => {
    mockJobState({ data: makeJobDetail({ status: "evaluated" }) });
    render(<JobDetail jobId={1} />);

    await userEvent.selectOptions(screen.getByTestId("status-dropdown"), "applied");
    expect(markMutate).toHaveBeenCalledWith({ status: "applied" });
  });

  it("toggles save through the mutation hook", async () => {
    mockJobState({ data: makeJobDetail({ saved: false }) });
    render(<JobDetail jobId={1} />);

    await userEvent.click(screen.getByTestId("save-star"));
    expect(savedMutate).toHaveBeenCalledWith(true);
  });
});
