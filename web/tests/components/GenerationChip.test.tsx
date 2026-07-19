import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { GenerationChip } from "../../src/components/GenerationChip";
import {
  useGenerate,
  useGeneration,
  useJobGenerations,
} from "../../src/hooks/useGeneration";
import { makeGeneration } from "../helpers";

jest.mock("../../src/hooks/useGeneration");

const mockedList = useJobGenerations as jest.MockedFunction<typeof useJobGenerations>;
const mockedGenerate = useGenerate as jest.MockedFunction<typeof useGenerate>;
const mockedPoll = useGeneration as jest.MockedFunction<typeof useGeneration>;

const generateMutate = jest.fn();

function mockList(data: ReturnType<typeof makeGeneration>[] | undefined) {
  mockedList.mockReturnValue({ data } as unknown as ReturnType<typeof useJobGenerations>);
}

function mockGenerate(isPending = false) {
  mockedGenerate.mockReturnValue({
    mutate: generateMutate,
    isPending,
  } as unknown as ReturnType<typeof useGenerate>);
}

beforeEach(() => {
  jest.clearAllMocks();
  mockGenerate();
  mockedPoll.mockReturnValue({ data: undefined } as unknown as ReturnType<typeof useGeneration>);
});

function chip() {
  return screen.getByTestId("generation-chip");
}

describe("<GenerationChip>", () => {
  it("renders the empty state and starts generation on click", async () => {
    mockList([]);
    render(<GenerationChip jobId={1} kind="resume" />);

    expect(chip()).toHaveAttribute("data-state", "empty");
    await userEvent.click(screen.getByRole("button", { name: /generate resume/i }));
    expect(generateMutate).toHaveBeenCalledWith("resume", expect.anything());
  });

  it("renders the pending state with a spinner while generating", () => {
    mockList([makeGeneration({ status: "pending", outcome: null })]);
    render(<GenerationChip jobId={1} kind="resume" />);

    expect(chip()).toHaveAttribute("data-state", "pending");
    expect(screen.getByTestId("generation-spinner")).toBeInTheDocument();
  });

  it("renders the failed state and re-generates on click", async () => {
    mockList([makeGeneration({ status: "failed", outcome: null })]);
    render(<GenerationChip jobId={1} kind="resume" />);

    expect(chip()).toHaveAttribute("data-state", "failed");
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(generateMutate).toHaveBeenCalledWith("resume", expect.anything());
  });

  it("renders the ready state with a dated download link", () => {
    mockList([makeGeneration({ status: "ready", outcome: "clean" })]);
    render(<GenerationChip jobId={1} kind="resume" />);

    expect(chip()).toHaveAttribute("data-state", "ready");
    const link = within(chip()).getByRole("link");
    expect(link).toHaveAttribute("href", "/api/generations/gen-abc123/download");
    expect(link).toHaveTextContent(/Resume · Jul 5/);
  });

  it("notes a repaired outcome beneath the ready download", () => {
    mockList([makeGeneration({ status: "ready", outcome: "repaired", repairNote: "x" })]);
    render(<GenerationChip jobId={1} kind="resume" />);

    expect(chip()).toHaveAttribute("data-state", "ready");
    expect(screen.getByText(/Auto-fixed/i)).toBeInTheDocument();
  });

  it("renders needs_review with locations only (never content) on expand", async () => {
    mockList([
      makeGeneration({
        status: "ready",
        outcome: "needs_review",
        reviewLocations: ["Experience → date range", "Summary → line 2"],
      }),
    ]);
    render(<GenerationChip jobId={1} kind="resume" />);

    expect(chip()).toHaveAttribute("data-state", "needs_review");
    // A download link is still offered.
    expect(within(chip()).getByRole("link")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /2 to check/i }));
    const locations = screen.getByTestId("review-locations");
    expect(within(locations).getByText(/Experience → date range/)).toBeInTheDocument();
    expect(within(locations).getByText(/Summary → line 2/)).toBeInTheDocument();
  });

  it("shows the cover-letter label for its kind", () => {
    mockList([makeGeneration({ kind: "cover_letter", status: "ready", outcome: "clean" })]);
    render(<GenerationChip jobId={1} kind="cover_letter" />);

    expect(chip()).toHaveAttribute("data-kind", "cover_letter");
    expect(within(chip()).getByRole("link")).toHaveTextContent(/Cover letter/);
  });
});
