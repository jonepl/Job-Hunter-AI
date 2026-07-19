import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { MasterResumePanel } from "../../src/components/MasterResumePanel";
import {
  useActivateResumeVersion,
  useResume,
  useUploadResume,
} from "../../src/hooks/useResume";
import { makeResume, makeResumeState } from "../helpers";

jest.mock("../../src/hooks/useResume");

const mockedUseResume = useResume as jest.MockedFunction<typeof useResume>;
const mockedUseUpload = useUploadResume as jest.MockedFunction<typeof useUploadResume>;
const mockedUseActivate = useActivateResumeVersion as jest.MockedFunction<
  typeof useActivateResumeVersion
>;

const uploadMutate = jest.fn();
const activateMutate = jest.fn();

function mockResumeState(state: Partial<ReturnType<typeof useResume>>) {
  mockedUseResume.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    ...state,
  } as unknown as ReturnType<typeof useResume>);
}

function mockUpload(state: Partial<ReturnType<typeof useUploadResume>> = {}) {
  mockedUseUpload.mockReturnValue({
    mutate: uploadMutate,
    isPending: false,
    isError: false,
    error: null,
    ...state,
  } as unknown as ReturnType<typeof useUploadResume>);
}

beforeEach(() => {
  jest.clearAllMocks();
  mockUpload();
  mockedUseActivate.mockReturnValue({
    mutate: activateMutate,
    isPending: false,
  } as unknown as ReturnType<typeof useActivateResumeVersion>);
});

describe("<MasterResumePanel>", () => {
  it("renders the active resume's provenance (never its content)", () => {
    mockResumeState({ data: makeResumeState({ versions: [makeResume()] }) });
    render(<MasterResumePanel />);

    const card = within(screen.getByTestId("resume-current-file"));
    expect(card.getByText("avery-reyes_master-resume.pdf")).toBeInTheDocument();
    expect(card.getByText(/v1 · uploaded .* · 214 KB · parsed 41 skills, 5 roles/)).toBeInTheDocument();
    expect(card.getByText("PDF")).toBeInTheDocument();
  });

  it("shows an empty state when no resume is stored", () => {
    mockResumeState({ data: makeResumeState({ active: null, versions: [] }) });
    render(<MasterResumePanel />);

    expect(screen.getByText(/No master resume stored yet/)).toBeInTheDocument();
    expect(screen.queryByTestId("resume-versions")).not.toBeInTheDocument();
  });

  it("uploads the selected file", async () => {
    mockResumeState({ data: makeResumeState({ active: null, versions: [] }) });
    render(<MasterResumePanel />);

    const file = new File(["bytes"], "new.pdf", { type: "application/pdf" });
    await userEvent.upload(screen.getByTestId("resume-file-input"), file);

    expect(uploadMutate).toHaveBeenCalledWith(file);
  });

  it("shows the server error message when an upload fails", () => {
    mockResumeState({ data: makeResumeState() });
    mockUpload({ isError: true, error: new Error("Resume is over the 5,000,000-byte limit.") });
    render(<MasterResumePanel />);

    expect(screen.getByRole("alert")).toHaveTextContent(/over the 5,000,000-byte limit/);
  });

  it("shows a parsing state while an upload is pending", () => {
    mockResumeState({ data: makeResumeState() });
    mockUpload({ isPending: true });
    render(<MasterResumePanel />);

    expect(screen.getByText(/Parsing resume/)).toBeInTheDocument();
  });

  it("lists version history and restores a non-active version", async () => {
    mockResumeState({
      data: makeResumeState({
        active: makeResume({ version: 2 }),
        versions: [
          makeResume({ version: 2, isActive: true }),
          makeResume({ version: 1, isActive: false, filename: "old.pdf" }),
        ],
      }),
    });
    render(<MasterResumePanel />);

    // The active version has no Restore; the older one does.
    const restoreButtons = screen.getAllByRole("button", { name: "Restore" });
    expect(restoreButtons).toHaveLength(1);

    await userEvent.click(restoreButtons[0]);
    expect(activateMutate).toHaveBeenCalledWith(1);
  });
});
