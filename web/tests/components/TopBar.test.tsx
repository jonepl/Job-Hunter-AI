import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { TopBar } from "../../src/components/TopBar";
import { renderWithRouter } from "../helpers";

describe("<TopBar>", () => {
  it("renders the wordmark on every screen", async () => {
    await renderWithRouter(<TopBar />);
    expect(screen.getByText("Job Hunter AI")).toBeInTheDocument();
  });

  it("renders the screen-specific center and right slots", async () => {
    await renderWithRouter(
      <TopBar center={<span data-testid="center-slot" />} right={<span data-testid="right-slot" />} />,
    );
    expect(screen.getByTestId("center-slot")).toBeInTheDocument();
    expect(screen.getByTestId("right-slot")).toBeInTheDocument();
  });

  it("fires the handler on a right-cluster gear button", async () => {
    const onClick = jest.fn();
    await renderWithRouter(
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
    await renderWithRouter(
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

  it("links the identity group back to search when off the home route", async () => {
    await renderWithRouter(<TopBar />, { initialEntries: ["/settings/voice"] });
    const link = screen.getByRole("link", { name: "Go to search home" });
    expect(link).toHaveAttribute("href", "/");
    expect(link).toContainElement(screen.getByText("Job Hunter AI"));
  });

  it("renders the identity group inert (no link) on the home route", async () => {
    await renderWithRouter(<TopBar />, { initialEntries: ["/"] });
    expect(screen.queryByRole("link", { name: "Go to search home" })).not.toBeInTheDocument();
    expect(screen.getByText("Job Hunter AI")).toBeInTheDocument();
  });
});
