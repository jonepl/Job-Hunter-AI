import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";

import { api } from "../../src/api/client";
import { jobsQueryKey } from "../../src/hooks/useJobs";
import { isRunDone, useRun, useStartRun } from "../../src/hooks/useRuns";
import { makeRun } from "../helpers";

jest.mock("../../src/api/client", () => ({
  api: {
    startRun: jest.fn(),
    getRun: jest.fn(),
    listRuns: jest.fn(),
  },
}));

const mockedStart = api.startRun as jest.MockedFunction<typeof api.startRun>;
const mockedGet = api.getRun as jest.MockedFunction<typeof api.getRun>;

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("isRunDone", () => {
  it("is true only for terminal statuses", () => {
    expect(isRunDone(makeRun({ status: "running" }))).toBe(false);
    expect(isRunDone(makeRun({ status: "succeeded" }))).toBe(true);
    expect(isRunDone(makeRun({ status: "failed" }))).toBe(true);
    expect(isRunDone(undefined)).toBe(false);
  });
});

describe("useStartRun", () => {
  it("starts a run and returns the running record", async () => {
    const { wrapper } = makeWrapper();
    mockedStart.mockResolvedValue(makeRun({ id: "r1", status: "running" }));

    const { result } = renderHook(() => useStartRun(), { wrapper });
    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe("r1");
  });
});

describe("useRun", () => {
  it("does not fetch when the id is null", () => {
    const { wrapper } = makeWrapper();
    renderHook(() => useRun(null), { wrapper });
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it("polls a run and invalidates the job list once it succeeds", async () => {
    const { client, wrapper } = makeWrapper();
    const invalidate = jest.spyOn(client, "invalidateQueries");
    mockedGet.mockResolvedValue(
      makeRun({ id: "r1", status: "succeeded", qualifying: 3 }),
    );

    const { result } = renderHook(() => useRun("r1"), { wrapper });

    await waitFor(() => expect(result.current.data?.status).toBe("succeeded"));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: jobsQueryKey });
  });
});
