import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { JobFilterBar } from "../../src/components/JobFilterBar";
import { makeJob } from "../helpers";

const jobs = [
  makeJob({ id: 1, status: "new" }),
  makeJob({ id: 2, status: "evaluated" }),
  makeJob({ id: 3, status: "applied" }),
  makeJob({ id: 4, status: "rejected", saved: true }),
];

describe("<JobFilterBar>", () => {
  it("renders a chip per filter with its count", () => {
    render(<JobFilterBar jobs={jobs} active="triage" onChange={jest.fn()} />);
    expect(screen.getByRole("button", { name: /Triage 2/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Pipeline 1/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /All 4/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Saved 1/ })).toBeInTheDocument();
  });

  it("marks the active chip as pressed", () => {
    render(<JobFilterBar jobs={jobs} active="pipeline" onChange={jest.fn()} />);
    expect(screen.getByRole("button", { name: /Pipeline/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: /Triage/ })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("calls onChange with the clicked filter id", async () => {
    const onChange = jest.fn();
    render(<JobFilterBar jobs={jobs} active="triage" onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: /Pipeline/ }));
    expect(onChange).toHaveBeenCalledWith("pipeline");
  });

  it("shows the active · total summary for the current view", () => {
    render(<JobFilterBar jobs={jobs} active="triage" onChange={jest.fn()} />);
    expect(screen.getByText(/active/)).toHaveTextContent("2 active · 4 total");
  });

  it("shows a clear affordance on a non-all filter and resets to all", async () => {
    const onChange = jest.fn();
    render(<JobFilterBar jobs={jobs} active="triage" onChange={onChange} />);
    const clear = screen.getByRole("button", { name: "Clear filter" });
    await userEvent.click(clear);
    expect(onChange).toHaveBeenCalledWith("all");
  });

  it("hides the clear affordance when All is active", () => {
    render(<JobFilterBar jobs={jobs} active="all" onChange={jest.fn()} />);
    expect(screen.queryByRole("button", { name: "Clear filter" })).not.toBeInTheDocument();
  });
});
