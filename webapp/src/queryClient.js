import { QueryClient } from '@tanstack/react-query'
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000,
      gcTime: 24 * 60 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      networkMode: 'offlineFirst',
    },
    mutations: { retry: 0 },
  },
})

export const queryPersister = typeof window !== 'undefined'
  ? createSyncStoragePersister({
      storage: window.localStorage,
      key: 'hayoc-heros:rq-cache:v4',
      throttleTime: 900,
    })
  : null

export const persistOptions = {
  persister: queryPersister,
  maxAge: 12 * 60 * 60 * 1000,
  buster: 'v4-live-events',
  dehydrateOptions: {
    shouldDehydrateQuery: (query) => query.meta?.persist !== false && query.state.status === 'success',
  },
}
