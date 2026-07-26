import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ConfigureProfileModal } from "../../src/components/ConfigureProfileModal";
import { api } from "../../src/api/client";
import { makeProfile, renderWithClient } from "../helpers";

jest.mock("../../src/api/client", () => ({
  api: { updateProfile: jest.fn() },
}));

const mockedUpdate = api.updateProfile as jest.MockedFunction<typeof api.updateProfile>;

beforeEach(() => {
  jest.clearAllMocks();
  mockedUpdate.mockResolvedValue(makeProfile({ id: 1 }));
});

const PROFILE = makeProfile({
  id: 1,
  name: "Backend",
  query: "Senior Software Engineer",
  location: "Remote",
  activeScrapers: ["linkedin", "indeed"],
  scheduleCron: "0 8 * * 1-5",
  scheduleEnabled: true,
  scoreThreshold: 82,
});

describe("<ConfigureProfileModal>", () => {
  it("pre-fills the editable fields from the profile", async () => {
    renderWithClient(<ConfigureProfileModal profile={PROFILE} onClose={jest.fn()} />);
    expect(screen.getByLabelText("Profile name")).toHaveValue("Backend");
    expect(screen.getByLabelText("Role / keywords")).toHaveValue("Senior Software Engineer");
    expect(screen.getByLabelText("Location")).toHaveValue("Remote");
    // LinkedIn + Indeed start pressed; Glassdoor does not.
    expect(screen.getByRole("button", { name: "LinkedIn" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Glassdoor" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("saves via PUT, preserving the schedule the modal does not expose", async () => {
    const onClose = jest.fn();
    renderWithClient(<ConfigureProfileModal profile={PROFILE} onClose={onClose} />);

    await userEvent.clear(screen.getByLabelText("Profile name"));
    await userEvent.type(screen.getByLabelText("Profile name"), "Backend v2");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(mockedUpdate).toHaveBeenCalledTimes(1));
    const [id, body] = mockedUpdate.mock.calls[0];
    expect(id).toBe(1);
    expect(body.name).toBe("Backend v2");
    // The schedule is carried through untouched (owned by the sibling editor).
    expect(body.scheduleCron).toBe("0 8 * * 1-5");
    expect(body.scheduleEnabled).toBe(true);
    expect(body.scoreThreshold).toBe(82);
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it("closes on Escape without saving", async () => {
    const onClose = jest.fn();
    renderWithClient(<ConfigureProfileModal profile={PROFILE} onClose={onClose} />);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
    expect(mockedUpdate).not.toHaveBeenCalled();
  });
});
