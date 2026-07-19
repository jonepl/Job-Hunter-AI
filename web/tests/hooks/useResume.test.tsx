import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";

import { api } from "../../src/api/client";
import {
  resumeQueryKey,
  useActivateResumeVersion,
  useResume,
  useUploadResume,
} from "../../src/hooks/useResume";
import { makeResume, makeResumeState } from "../helpers";

jest.mock("../../src/api/client", () => ({
  api: { getResume: jest.fn(), uploadResume: jest.fn(), activateResumeVersion: jest.fn() },
}));

const mockedGet = api.getResume as jest.MockedFunction<typeof api.getResume>;
const mockedUpload = api.uploadResume as jest.MockedFunction<typeof api.uploadResume>;
const mockedActivate = api.activateResumeVersion as jest.MockedFunction<
  typeof api.activateResumeVersion
>;

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

describe("useResume", () => {
  it("returns the resume state fetched from the client", async () => {
    const { wrapper } = makeWrapper();
    mockedGet.mockResolvedValue(makeResumeState());

    const { result } = renderHook(() => useResume(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.active?.version).toBe(1);
  });
});

describe("useUploadResume", () => {
  it("uploads the file and writes the returned state into the cache", async () => {
    const { client, wrapper } = makeWrapper();
    const next = makeResumeState({
      versions: [makeResume({ version: 2 }), makeResume({ version: 1, isActive: false })],
      active: makeResume({ version: 2 }),
    });
    mockedUpload.mockResolvedValue(next);

    const { result } = renderHook(() => useUploadResume(), { wrapper });
    const file = new File(["bytes"], "resume.pdf", { type: "application/pdf" });
    act(() => result.current.mutate(file));

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedUpload).toHaveBeenCalledWith(file);
    expect(client.getQueryData(resumeQueryKey)).toEqual(next);
  });
});

describe("useActivateResumeVersion", () => {
  it("activates a version and caches the returned state", async () => {
    const { client, wrapper } = makeWrapper();
    const restored = makeResumeState({
      versions: [makeResume({ version: 2, isActive: false }), makeResume({ version: 1 })],
      active: makeResume({ version: 1 }),
    });
    mockedActivate.mockResolvedValue(restored);

    const { result } = renderHook(() => useActivateResumeVersion(), { wrapper });
    act(() => result.current.mutate(1));

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedActivate).toHaveBeenCalledWith(1);
    expect(client.getQueryData(resumeQueryKey)).toEqual(restored);
  });
});
