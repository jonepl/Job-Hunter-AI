import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";

import { api } from "../../src/api/client";
import { useJobs } from "../../src/hooks/useJobs";
import { makeJob } from "../helpers";

jest.mock("../../src/api/client", () => ({
  api: { listJobs: jest.fn() },
}));

const mockedListJobs = api.listJobs as jest.MockedFunction<typeof api.listJobs>;

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe("useJobs", () => {
  it("returns the jobs fetched from the API client", async () => {
    mockedListJobs.mockResolvedValue([makeJob({ id: 7, title: "Fetched Role" })]);

    const { result } = renderHook(() => useJobs(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].title).toBe("Fetched Role");
  });
});
