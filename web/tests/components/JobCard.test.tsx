import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { JobCard } from "../../src/components/JobCard";
import { makeJob } from "../helpers";

describe("<JobCard>", () => {
  it("renders the job's identity, providers, and score", () => {
    render(
      <JobCard
        job={makeJob({
          title: "Staff Engineer",
          company: "Northwind",
          location: "Remote",
          platforms: ["linkedin", "indeed"],
          score: 82,
        })}
      />,
    );

    expect(screen.getByText("Staff Engineer")).toBeInTheDocument();
    expect(screen.getByText(/Northwind/)).toBeInTheDocument();
    expect(screen.getByText("via LinkedIn, Indeed")).toBeInTheDocument();
    expect(screen.getByTestId("score-chip")).toHaveAttribute("data-state", "qualify");
    expect(screen.getByTestId("score-chip")).toHaveTextContent("82 · Qualifying");
  });

  it("calls onSelect with the job id when clicked", async () => {
    const onSelect = jest.fn();
    render(<JobCard job={makeJob({ id: 42 })} onSelect={onSelect} />);

    await userEvent.click(screen.getByTestId("job-card"));
    expect(onSelect).toHaveBeenCalledWith(42);
  });

  it("reflects the selected state for assistive tech", () => {
    render(<JobCard job={makeJob()} selected />);
    expect(screen.getByTestId("job-card")).toHaveAttribute("data-selected", "true");
    expect(screen.getByTestId("job-card")).toHaveAttribute("aria-pressed", "true");
  });

  it("shows a status pill only once a job leaves the machine states", () => {
    const { rerender } = render(<JobCard job={makeJob({ status: "evaluated" })} />);
    expect(screen.queryByTestId("status-pill")).not.toBeInTheDocument();

    rerender(<JobCard job={makeJob({ status: "applied" })} />);
    expect(screen.getByTestId("status-pill")).toHaveTextContent("Applied");
  });

  it("marks a saved job with a star", () => {
    render(<JobCard job={makeJob({ saved: true })} />);
    expect(screen.getByLabelText("Saved")).toBeInTheDocument();
  });
});
