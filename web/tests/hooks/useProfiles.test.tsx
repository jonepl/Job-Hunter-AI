import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";

import { api } from "../../src/api/client";
import {
  profilesQueryKey,
  useCreateProfile,
  useDeleteProfile,
  useProfiles,
  useUpdateProfile,
} from "../../src/hooks/useProfiles";
import { makeProfile } from "../helpers";

jest.mock("../../src/api/client", () => ({
  api: {
    listProfiles: jest.fn(),
    createProfile: jest.fn(),
    updateProfile: jest.fn(),
    deleteProfile: jest.fn(),
  },
}));

const mockedList = api.listProfiles as jest.MockedFunction<typeof api.listProfiles>;
const mockedCreate = api.createProfile as jest.MockedFunction<typeof api.createProfile>;
const mockedUpdate = api.updateProfile as jest.MockedFunction<typeof api.updateProfile>;
const mockedDelete = api.deleteProfile as jest.MockedFunction<typeof api.deleteProfile>;

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

describe("useProfiles", () => {
  it("loads the profile list", async () => {
    const { wrapper } = makeWrapper();
    mockedList.mockResolvedValue([makeProfile({ name: "A" })]);

    const { result } = renderHook(() => useProfiles(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0].name).toBe("A");
  });
});

describe("profile mutations invalidate the list", () => {
  const asProfileIn = () => {
    const { id: _id, ...body } = makeProfile();
    return body;
  };

  it("create invalidates the list", async () => {
    const { client, wrapper } = makeWrapper();
    mockedCreate.mockResolvedValue(makeProfile());
    const spy = jest.spyOn(client, "invalidateQueries");

    const { result } = renderHook(() => useCreateProfile(), { wrapper });
    act(() => result.current.mutate(asProfileIn()));

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(spy).toHaveBeenCalledWith({ queryKey: profilesQueryKey });
  });

  it("update invalidates the list", async () => {
    const { client, wrapper } = makeWrapper();
    mockedUpdate.mockResolvedValue(makeProfile());
    const spy = jest.spyOn(client, "invalidateQueries");

    const { result } = renderHook(() => useUpdateProfile(), { wrapper });
    act(() => result.current.mutate({ id: 1, body: asProfileIn() }));

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(spy).toHaveBeenCalledWith({ queryKey: profilesQueryKey });
  });

  it("delete invalidates the list", async () => {
    const { client, wrapper } = makeWrapper();
    mockedDelete.mockResolvedValue(undefined);
    const spy = jest.spyOn(client, "invalidateQueries");

    const { result } = renderHook(() => useDeleteProfile(), { wrapper });
    act(() => result.current.mutate(1));

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(spy).toHaveBeenCalledWith({ queryKey: profilesQueryKey });
  });
});
