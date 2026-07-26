import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";

import { api } from "../../src/api/client";
import { jobsQueryKey } from "../../src/hooks/useJobs";
import {
  isRunDone,
  useRun,
  useRunProfilesSequentially,
  useRuns,
  useStartRun,
} from "../../src/hooks/useRuns";
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
const mockedList = api.listRuns as jest.MockedFunction<typeof api.listRuns>;

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

describe("useRuns", () => {
  it("fetches the global list by default and a scoped list per profile", async () => {
    const { wrapper } = makeWrapper();
    mockedList.mockResolvedValue([]);

    const global = renderHook(() => useRuns(), { wrapper });
    const scoped = renderHook(() => useRuns(7), { wrapper });

    await waitFor(() => expect(global.result.current.isSuccess).toBe(true));
    await waitFor(() => expect(scoped.result.current.isSuccess).toBe(true));

    expect(mockedList).toHaveBeenCalledWith(undefined);
    expect(mockedList).toHaveBeenCalledWith(7);
  });
});

describe("useRunProfilesSequentially", () => {
  it("runs profiles one at a time, in order, and reports completion", async () => {
    const { wrapper } = makeWrapper();
    // Each run starts already-terminal so the poll loop returns without waiting.
    mockedStart.mockImplementation(async (id) =>
      makeRun({ id: `run-${id}`, status: "succeeded", profileId: id }),
    );

    const { result } = renderHook(() => useRunProfilesSequentially(0), { wrapper });
    await act(async () => {
      await result.current.start([1, 2, 3]);
    });

    await waitFor(() => expect(result.current.running).toBe(false));
    expect(mockedStart.mock.calls.map((c) => c[0])).toEqual([1, 2, 3]);
    expect(result.current.current).toBe(3);
    expect(result.current.error).toBeNull();
  });

  it("halts the batch when a run fails and surfaces its error", async () => {
    const { wrapper } = makeWrapper();
    mockedStart.mockImplementation(async (id) =>
      id === 2
        ? makeRun({ id: "run-2", status: "failed", error: "TimeoutError", profileId: 2 })
        : makeRun({ id: `run-${id}`, status: "succeeded", profileId: id }),
    );

    const { result } = renderHook(() => useRunProfilesSequentially(0), { wrapper });
    await act(async () => {
      await result.current.start([1, 2, 3]);
    });

    await waitFor(() => expect(result.current.running).toBe(false));
    // Stopped after the second profile — the third never started.
    expect(mockedStart.mock.calls.map((c) => c[0])).toEqual([1, 2]);
    expect(result.current.error).toBe("TimeoutError");
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
