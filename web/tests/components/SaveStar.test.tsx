import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SaveStar } from "../../src/components/SaveStar";

describe("<SaveStar>", () => {
  it("toggles from unsaved to saved", async () => {
    const onToggle = jest.fn();
    render(<SaveStar saved={false} onToggle={onToggle} />);

    const button = screen.getByTestId("save-star");
    expect(button).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(button);
    expect(onToggle).toHaveBeenCalledWith(true);
  });

  it("toggles from saved to unsaved", async () => {
    const onToggle = jest.fn();
    render(<SaveStar saved onToggle={onToggle} />);

    expect(screen.getByTestId("save-star")).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByTestId("save-star"));
    expect(onToggle).toHaveBeenCalledWith(false);
  });
});
