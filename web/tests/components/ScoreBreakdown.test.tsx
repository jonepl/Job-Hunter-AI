import { render, screen } from "@testing-library/react";

import { ScoreBreakdown } from "../../src/components/ScoreBreakdown";
import { makeJobDetail } from "../helpers";

describe("<ScoreBreakdown>", () => {
  it("renders one row per category with a humanized label and earned/max", () => {
    const breakdown = makeJobDetail().scoreBreakdown!;
    render(<ScoreBreakdown breakdown={breakdown} />);

    const rows = screen.getByTestId("score-breakdown").querySelectorAll("li");
    expect(rows).toHaveLength(9);
    expect(screen.getByText("Role alignment")).toBeInTheDocument();
    expect(screen.getByText("Technical stack match")).toBeInTheDocument();
    expect(screen.getAllByText("8/10")).toHaveLength(9);
  });
});
