import { render, screen } from "@testing-library/react";

import { ThresholdRail } from "../../src/components/ThresholdRail";

describe("<ThresholdRail>", () => {
  it("marks a qualifying score", () => {
    render(<ThresholdRail score={82} threshold={70} nearMissFloor={55} />);
    expect(screen.getByTestId("threshold-rail")).toHaveAttribute("data-state", "qualify");
  });

  it("marks a near-miss score", () => {
    render(<ThresholdRail score={62} threshold={70} nearMissFloor={55} />);
    expect(screen.getByTestId("threshold-rail")).toHaveAttribute("data-state", "nearmiss");
  });

  it("marks a below score", () => {
    render(<ThresholdRail score={40} threshold={70} nearMissFloor={55} />);
    expect(screen.getByTestId("threshold-rail")).toHaveAttribute("data-state", "below");
  });

  it("renders the threshold tick with its value", () => {
    render(<ThresholdRail score={82} threshold={70} nearMissFloor={55} />);
    expect(screen.getByTestId("threshold-rail-tick")).toBeInTheDocument();
    expect(screen.getByText("70")).toBeInTheDocument();
  });

  it("omits the tick when there is no threshold", () => {
    render(<ThresholdRail score={null} threshold={null} nearMissFloor={null} />);
    expect(screen.queryByTestId("threshold-rail-tick")).not.toBeInTheDocument();
  });
});
