import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { api } from './api.js'

export function useMetaQuery() {
  return useQuery({ queryKey: ['meta'], queryFn: api.meta, staleTime: 5 * 60_000, meta: { persist: true } })
}

export function useRandomHeroesQuery(limit = 6) {
  return useQuery({ queryKey: ['heroes', 'random', limit], queryFn: () => api.random(limit), staleTime: 90_000, meta: { persist: true } })
}

export function useHeroQuery(id) {
  return useQuery({ queryKey: ['hero', id], queryFn: () => api.hero(id), enabled: Boolean(id), staleTime: 30 * 60_000, meta: { persist: true } })
}

export function useHeroesInfiniteQuery({ q = '', war = '', region = '', limit = 18 }) {
  return useInfiniteQuery({
    queryKey: ['heroes', 'list', { q, war, region, limit }],
    queryFn: ({ pageParam }) => api.heroes({ q, war, region, page: pageParam, limit }),
    initialPageParam: 1,
    getNextPageParam: (last) => last?.pagination?.hasMore ? last.pagination.page + 1 : undefined,
    staleTime: 3 * 60_000,
    meta: { persist: true },
  })
}

export function useUpcomingEventsQuery(limit = 8) {
  return useQuery({ queryKey: ['events', 'upcoming', limit], queryFn: () => api.upcomingEvents(limit), staleTime: 15_000, refetchOnMount: 'always', refetchOnWindowFocus: true, refetchInterval: 30_000, meta: { persist: false } })
}

export function useEventsQuery() {
  return useQuery({ queryKey: ['events', 'all'], queryFn: () => api.events({ limit: 300 }), staleTime: 15_000, refetchOnMount: 'always', refetchOnWindowFocus: true, refetchInterval: 30_000, meta: { persist: false } })
}

export function useEventQuery(id) {
  return useQuery({ queryKey: ['event', id], queryFn: () => api.event(id), enabled: Boolean(id), staleTime: 15_000, refetchOnMount: 'always', refetchOnWindowFocus: true, meta: { persist: false } })
}

export function useEventReminderQuery(id, enabled) {
  return useQuery({ queryKey: ['reminder', 'event', id], queryFn: () => api.eventReminder(id), enabled: Boolean(enabled && id), staleTime: 15_000, meta: { persist: false } })
}

export function useRemindersQuery(enabled) {
  return useQuery({ queryKey: ['reminders'], queryFn: api.reminders, enabled: Boolean(enabled), staleTime: 15_000, meta: { persist: false } })
}

export function useMeQuery(enabled) {
  return useQuery({ queryKey: ['me'], queryFn: api.me, enabled, staleTime: 30_000, meta: { persist: false } })
}
