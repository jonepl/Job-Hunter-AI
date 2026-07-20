import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { TopBar } from "../../src/components/TopBar";

describe("<TopBar>", () => {
  it("renders the wordmark on every screen", () => {
    render(<TopBar />);
    expect(screen.getByText("Job Hunter AI")).toBeInTheDocument();
  });

  it("renders the screen-specific center and right slots", () => {
    render(
      <TopBar center={<span data-testid="center-slot" />} right={<span data-testid="right-slot" />} />,
    );
    expect(screen.getByTestId("center-slot")).toBeInTheDocument();
    expect(screen.getByTestId("right-slot")).toBeInTheDocument();
  });

  it("fires the handler on a right-cluster gear button", async () => {
    const onClick = jest.fn();
    render(
      <TopBar
        right={
          <button type="button" aria-label="Settings" onClick={onClick}>
            gear
          </button>
        }
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    expect(onClick).toHaveBeenCalled();
  });

  it("fires the handler on a right-cluster back button", async () => {
    const onClick = jest.fn();
    render(
      <TopBar
        right={
          <button type="button" onClick={onClick}>
            ← Back to search
          </button>
        }
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /Back to search/ }));
    expect(onClick).toHaveBeenCalled();
  });
});
