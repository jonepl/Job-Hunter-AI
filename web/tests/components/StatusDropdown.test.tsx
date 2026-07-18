import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { StatusDropdown } from "../../src/components/StatusDropdown";

describe("<StatusDropdown>", () => {
  it("offers exactly the six human statuses", () => {
    render(<StatusDropdown value="evaluated" onChange={jest.fn()} />);
    const options = screen.getAllByRole("option");
    const enabled = options.filter((o) => !(o as HTMLOptionElement).disabled);
    expect(enabled.map((o) => (o as HTMLOptionElement).value)).toEqual([
      "applied",
      "started",
      "interviewing",
      "offer",
      "rejected",
      "not_interested",
    ]);
  });

  it("shows a machine status as the current, non-selectable value", () => {
    render(<StatusDropdown value="evaluated" onChange={jest.fn()} />);
    const current = screen.getByRole("option", { name: "Evaluated" }) as HTMLOptionElement;
    expect(current.disabled).toBe(true);
    expect(current.selected).toBe(true);
  });

  it("fires onChange with the chosen human status", async () => {
    const onChange = jest.fn();
    render(<StatusDropdown value="evaluated" onChange={onChange} />);
    await userEvent.selectOptions(screen.getByTestId("status-dropdown"), "applied");
    expect(onChange).toHaveBeenCalledWith("applied");
  });

  it("soft-confirms reactivation of a terminal status", async () => {
    const onChange = jest.fn();
    const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(false);
    render(<StatusDropdown value="rejected" onChange={onChange} />);

    await userEvent.selectOptions(screen.getByTestId("status-dropdown"), "applied");
    expect(confirmSpy).toHaveBeenCalled();
    expect(onChange).not.toHaveBeenCalled(); // declined

    confirmSpy.mockReturnValue(true);
    await userEvent.selectOptions(screen.getByTestId("status-dropdown"), "applied");
    expect(onChange).toHaveBeenCalledWith("applied");
    confirmSpy.mockRestore();
  });
});
