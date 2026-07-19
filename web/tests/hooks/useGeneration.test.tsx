import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";

import { api } from "../../src/api/client";
import {
  jobGenerationsQueryKey,
  useGenerate,
  useGeneration,
  useJobGenerations,
} from "../../src/hooks/useGeneration";
import { makeGeneration } from "../helpers";

jest.mock("../../src/api/client", () => ({
  api: {
    listJobGenerations: jest.fn(),
    generate: jest.fn(),
    getGeneration: jest.fn(),
  },
  generationDownloadUrl: (id: string) => `/api/generations/${id}/download`,
}));

const mockedList = api.listJobGenerations as jest.MockedFunction<
  typeof api.listJobGenerations
>;
const mockedGenerate = api.generate as jest.MockedFunction<typeof api.generate>;
const mockedGet = api.getGeneration as jest.MockedFunction<typeof api.getGeneration>;

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

describe("useJobGenerations", () => {
  it("loads the job's recorded generations", async () => {
    const { wrapper } = makeWrapper();
    mockedList.mockResolvedValue([makeGeneration()]);

    const { result } = renderHook(() => useJobGenerations(1), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0].id).toBe("gen-abc123");
  });
});

describe("useGenerate", () => {
  it("POSTs the kind and invalidates the job's generation list", async () => {
    const { client, wrapper } = makeWrapper();
    const pending = makeGeneration({ status: "pending", outcome: null });
    mockedGenerate.mockResolvedValue(pending);
    const spy = jest.spyOn(client, "invalidateQueries");

    const { result } = renderHook(() => useGenerate(1), { wrapper });
    act(() => result.current.mutate("resume"));

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedGenerate).toHaveBeenCalledWith(1, "resume");
    expect(spy).toHaveBeenCalledWith({ queryKey: jobGenerationsQueryKey(1) });
  });
});

describe("useGeneration", () => {
  it("is disabled when no id is polled", () => {
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useGeneration(null, 1), { wrapper });
    expect(result.current.fetchStatus).toBe("idle");
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it("polls a generation and stops once it is terminal", async () => {
    const { wrapper } = makeWrapper();
    mockedGet.mockResolvedValue(makeGeneration({ status: "ready" }));

    const { result } = renderHook(() => useGeneration("gen-abc123", 1), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.status).toBe("ready");
    // Terminal status → refetchInterval is false, so no repeat polling is scheduled.
    expect(mockedGet).toHaveBeenCalledTimes(1);
  });
});
