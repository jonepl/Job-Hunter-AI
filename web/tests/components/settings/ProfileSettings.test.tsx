import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ProfileSettings } from "../../../src/components/settings/ProfileSettings";
import { api } from "../../../src/api/client";
import { makeProfile, renderWithClient } from "../../helpers";

jest.mock("../../../src/api/client", () => ({
  api: {
    listProfiles: jest.fn(),
    createProfile: jest.fn(),
    updateProfile: jest.fn(),
    deleteProfile: jest.fn(),
  },
}));

const mockedList = api.listProfiles as jest.MockedFunction<typeof api.listProfiles>;
const mockedCreate = api.createProfile as jest.MockedFunction<typeof api.createProfile>;
const mockedDelete = api.deleteProfile as jest.MockedFunction<typeof api.deleteProfile>;

beforeEach(() => {
  jest.clearAllMocks();
  mockedList.mockResolvedValue([
    makeProfile({ id: 1, name: "Backend" }),
    makeProfile({ id: 2, name: "Frontend" }),
  ]);
  mockedCreate.mockResolvedValue(makeProfile({ id: 3, name: "New" }));
  mockedDelete.mockResolvedValue(undefined);
});

describe("<ProfileSettings>", () => {
  it("lists the stored profiles", async () => {
    renderWithClient(<ProfileSettings />);
    const list = await screen.findByTestId("profile-list");
    expect(list).toHaveTextContent("Backend");
    expect(list).toHaveTextContent("Frontend");
  });

  it("creates a profile through the editor", async () => {
    renderWithClient(<ProfileSettings />);
    await screen.findByTestId("profile-list");

    await userEvent.click(screen.getByRole("button", { name: "Add profile" }));
    await userEvent.type(screen.getByLabelText("Query"), "Staff Engineer");
    await userEvent.click(screen.getByRole("button", { name: /Save profile/ }));

    await waitFor(() => expect(mockedCreate).toHaveBeenCalled());
    expect(mockedCreate.mock.calls[0][0].query).toBe("Staff Engineer");
  });

  it("deletes a non-last profile", async () => {
    renderWithClient(<ProfileSettings />);
    await screen.findByTestId("profile-list");

    await userEvent.click(screen.getByRole("button", { name: "Delete Backend" }));
    await waitFor(() => expect(mockedDelete).toHaveBeenCalledWith(1));
  });
});
