import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Settings } from "../../src/screens/Settings";

// The panel is exercised in its own test; stub it here so Settings tests focus on
// the shell (rail + back control).
jest.mock("../../src/components/MasterResumePanel", () => ({
  MasterResumePanel: () => <div data-testid="master-resume-panel" />,
}));

describe("<Settings>", () => {
  it("renders the CONFIGURATION rail with only Master resume active", () => {
    render(<Settings onBack={jest.fn()} />);

    const resume = screen.getByRole("button", { name: /Master resume/ });
    expect(resume).toHaveAttribute("aria-current", "page");
    expect(resume).not.toBeDisabled();

    // The other five sections are present but disabled placeholders (W7).
    expect(screen.getByRole("button", { name: /Voice & tone/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Match threshold/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Run schedule/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Search profiles/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Evaluator provider/ })).toBeDisabled();
  });

  it("renders the master resume panel", () => {
    render(<Settings onBack={jest.fn()} />);
    expect(screen.getByTestId("master-resume-panel")).toBeInTheDocument();
  });

  it("invokes onBack from the back control", async () => {
    const onBack = jest.fn();
    render(<Settings onBack={onBack} />);

    await userEvent.click(screen.getByRole("button", { name: /Back to search/ }));
    expect(onBack).toHaveBeenCalled();
  });
});
