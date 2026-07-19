import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ThresholdSettings } from "../../../src/components/settings/ThresholdSettings";
import { api } from "../../../src/api/client";
import { makeProfile, renderWithClient } from "../../helpers";

jest.mock("../../../src/api/client", () => ({
  api: { listProfiles: jest.fn(), updateProfile: jest.fn() },
}));

const mockedList = api.listProfiles as jest.MockedFunction<typeof api.listProfiles>;
const mockedUpdate = api.updateProfile as jest.MockedFunction<typeof api.updateProfile>;

beforeEach(() => {
  jest.clearAllMocks();
  mockedList.mockResolvedValue([makeProfile({ id: 3, scoreThreshold: 70 })]);
  mockedUpdate.mockResolvedValue(makeProfile({ id: 3, scoreThreshold: 85 }));
});

describe("<ThresholdSettings>", () => {
  it("writes the selected profile's threshold", async () => {
    renderWithClient(<ThresholdSettings />);
    await screen.findByTestId("threshold-settings");

    fireEvent.change(screen.getByLabelText("Threshold"), { target: { value: "85" } });
    expect(screen.getByTestId("threshold-value")).toHaveTextContent("85");

    await userEvent.click(screen.getByRole("button", { name: /Save threshold/ }));
    await waitFor(() => expect(mockedUpdate).toHaveBeenCalled());
    const call = mockedUpdate.mock.calls[0];
    expect(call[0]).toBe(3);
    expect(call[1].scoreThreshold).toBe(85);
  });
});
