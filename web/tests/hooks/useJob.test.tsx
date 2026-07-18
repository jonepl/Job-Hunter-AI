import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";

import { api } from "../../src/api/client";
import { useMarkStatus, useSaved } from "../../src/hooks/useJob";
import { jobsQueryKey } from "../../src/hooks/useJobs";
import { jobQueryKey } from "../../src/hooks/useJob";
import { makeJob, makeJobDetail } from "../helpers";

jest.mock("../../src/api/client", () => ({
  api: { markStatus: jest.fn(), setSaved: jest.fn() },
}));

const mockedMarkStatus = api.markStatus as jest.MockedFunction<typeof api.markStatus>;
const mockedSetSaved = api.setSaved as jest.MockedFunction<typeof api.setSaved>;

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  // Seed both caches so optimistic patches have something to update.
  client.setQueryData(jobsQueryKey, [makeJob({ id: 1, status: "evaluated" })]);
  client.setQueryData(jobQueryKey(1), makeJobDetail({ id: 1, status: "evaluated" }));
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

describe("useMarkStatus", () => {
  it("optimistically updates both caches before the request resolves", async () => {
    const { client, wrapper } = makeWrapper();
    let resolve!: (v: unknown) => void;
    mockedMarkStatus.mockReturnValue(new Promise((r) => (resolve = r)) as never);

    const { result } = renderHook(() => useMarkStatus(1), { wrapper });
    act(() => result.current.mutate({ status: "applied" }));

    // Optimistic patch is visible immediately, before the promise resolves.
    await waitFor(() => {
      expect(client.getQueryData<{ status: string }>(jobQueryKey(1))?.status).toBe("applied");
    });
    const list = client.getQueryData<{ status: string }[]>(jobsQueryKey);
    expect(list?.[0].status).toBe("applied");

    act(() => resolve(makeJobDetail({ id: 1, status: "applied" })));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it("rolls back both caches when the request fails", async () => {
    const { client, wrapper } = makeWrapper();
    mockedMarkStatus.mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useMarkStatus(1), { wrapper });
    act(() => result.current.mutate({ status: "applied" }));

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(client.getQueryData<{ status: string }>(jobQueryKey(1))?.status).toBe("evaluated");
    expect(client.getQueryData<{ status: string }[]>(jobsQueryKey)?.[0].status).toBe("evaluated");
  });
});

describe("useSaved", () => {
  it("optimistically flips saved and rolls back on error", async () => {
    const { client, wrapper } = makeWrapper();
    mockedSetSaved.mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useSaved(1), { wrapper });
    act(() => result.current.mutate(true));

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(client.getQueryData<{ saved: boolean }>(jobQueryKey(1))?.saved).toBe(false);
  });
});
