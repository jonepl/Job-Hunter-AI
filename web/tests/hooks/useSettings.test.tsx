import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";

import { api } from "../../src/api/client";
import {
  settingsQueryKey,
  useClearSecret,
  useSetSecret,
  useSettings,
  useUpdateSettings,
} from "../../src/hooks/useSettings";
import { settingsToUpdate } from "../../src/lib/settings";
import { makeSecretStatus, makeSettings } from "../helpers";

jest.mock("../../src/api/client", () => ({
  api: {
    getSettings: jest.fn(),
    updateSettings: jest.fn(),
    setSecret: jest.fn(),
    clearSecret: jest.fn(),
  },
}));

const mockedGet = api.getSettings as jest.MockedFunction<typeof api.getSettings>;
const mockedUpdate = api.updateSettings as jest.MockedFunction<typeof api.updateSettings>;
const mockedSet = api.setSecret as jest.MockedFunction<typeof api.setSecret>;
const mockedClear = api.clearSecret as jest.MockedFunction<typeof api.clearSecret>;

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

describe("useSettings", () => {
  it("loads the settings state", async () => {
    const { wrapper } = makeWrapper();
    mockedGet.mockResolvedValue(makeSettings({ evaluatorProvider: "anthropic" }));

    const { result } = renderHook(() => useSettings(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.evaluatorProvider).toBe("anthropic");
  });
});

describe("useUpdateSettings", () => {
  it("updates and caches the returned state", async () => {
    const { client, wrapper } = makeWrapper();
    const next = makeSettings({ enrichmentMode: "enforce" });
    mockedUpdate.mockResolvedValue(next);

    const { result } = renderHook(() => useUpdateSettings(), { wrapper });
    act(() => result.current.mutate(settingsToUpdate(makeSettings())));

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(client.getQueryData(settingsQueryKey)).toEqual(next);
  });
});

describe("secret mutations", () => {
  it("setSecret invalidates settings", async () => {
    const { client, wrapper } = makeWrapper();
    mockedSet.mockResolvedValue(makeSecretStatus({ overridden: true }));
    const spy = jest.spyOn(client, "invalidateQueries");

    const { result } = renderHook(() => useSetSecret(), { wrapper });
    act(() => result.current.mutate({ name: "openai_api_key", value: "sk-x" }));

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedSet).toHaveBeenCalledWith("openai_api_key", "sk-x");
    expect(spy).toHaveBeenCalledWith({ queryKey: settingsQueryKey });
  });

  it("clearSecret invalidates settings", async () => {
    const { client, wrapper } = makeWrapper();
    mockedClear.mockResolvedValue(makeSecretStatus());
    const spy = jest.spyOn(client, "invalidateQueries");

    const { result } = renderHook(() => useClearSecret(), { wrapper });
    act(() => result.current.mutate("openai_api_key"));

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedClear).toHaveBeenCalledWith("openai_api_key");
    expect(spy).toHaveBeenCalledWith({ queryKey: settingsQueryKey });
  });
});
