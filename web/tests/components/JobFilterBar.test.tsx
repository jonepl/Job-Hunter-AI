import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { JobFilterBar } from "../../src/components/JobFilterBar";
import { EMPTY_FILTER, type FilterState } from "../../src/lib/filters";
import { makeJob } from "../helpers";

const jobs = [
  makeJob({ id: 1, status: "applied", score: 90, threshold: 70, nearMissFloor: 55 }),
  makeJob({ id: 2, status: "applied", score: 60, threshold: 70, nearMissFloor: 55 }),
  makeJob({ id: 3, status: "interviewing", score: 80, threshold: 70, nearMissFloor: 55, saved: true }),
];

describe("<JobFilterBar>", () => {
  it("toggles a status label through onChange", async () => {
    const onChange = jest.fn();
    render(<JobFilterBar jobs={jobs} filter={EMPTY_FILTER} onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: /Applied/ }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ labels: ["applied"] }));
  });

  it("toggles qualifying-only independently of the labels", async () => {
    const onChange = jest.fn();
    render(<JobFilterBar jobs={jobs} filter={EMPTY_FILTER} onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: /Qualifying only/ }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ qualifyingOnly: true }));
  });

  it("shows a Clear affordance only when a filter is active", async () => {
    const onChange = jest.fn();
    const active: FilterState = { ...EMPTY_FILTER, saved: true };
    const { rerender } = render(
      <JobFilterBar jobs={jobs} filter={EMPTY_FILTER} onChange={onChange} />,
    );
    expect(screen.queryByRole("button", { name: "Clear" })).not.toBeInTheDocument();

    rerender(<JobFilterBar jobs={jobs} filter={active} onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(onChange).toHaveBeenCalledWith(EMPTY_FILTER);
  });

  it("reflects the active state on a pressed chip", () => {
    const filter: FilterState = { ...EMPTY_FILTER, labels: ["applied"] };
    render(<JobFilterBar jobs={jobs} filter={filter} onChange={jest.fn()} />);
    expect(screen.getByRole("button", { name: /Applied/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Interviewing/ })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });
});
