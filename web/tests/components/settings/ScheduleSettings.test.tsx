import { screen, waitFor, within } from "@testing-library/react";

import { ScheduleSettings } from "../../../src/components/settings/ScheduleSettings";
import { api } from "../../../src/api/client";
import { makeSettings, renderWithClient } from "../../helpers";

jest.mock("../../../src/api/client", () => ({
  api: {
    getSettings: jest.fn(),
    updateSettings: jest.fn(),
    getSchedulePreview: jest.fn(),
  },
}));

const mockedGet = api.getSettings as jest.MockedFunction<typeof api.getSettings>;
const mockedPreview = api.getSchedulePreview as jest.MockedFunction<
  typeof api.getSchedulePreview
>;

beforeEach(() => {
  jest.clearAllMocks();
  mockedGet.mockResolvedValue(makeSettings({ scheduleCron: "0 9 * * *" }));
  mockedPreview.mockResolvedValue({
    nextRuns: [
      "2026-07-20T09:00:00Z",
      "2026-07-21T09:00:00Z",
      "2026-07-22T09:00:00Z",
    ],
  });
});

describe("<ScheduleSettings>", () => {
  it("lists the next three runs from the preview", async () => {
    renderWithClient(<ScheduleSettings />);

    const preview = await screen.findByTestId("schedule-preview");
    // Wait past the 400ms debounce for the preview query to resolve.
    await waitFor(
      () => expect(within(preview).getAllByRole("listitem")).toHaveLength(3),
      { timeout: 3000 },
    );
  });
});
