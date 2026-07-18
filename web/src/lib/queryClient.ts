import { QueryClient } from "@tanstack/react-query";

// In-memory server-state cache. No browser storage (design rule): the cache
// lives only for the session.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});
