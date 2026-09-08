import type { Catalog, Schedule, SyncStatus, Window } from '../types/schedule'

export type JsonRequest = (path: string, options?: { query?: Record<string, string>; signal?: AbortSignal }) => Promise<unknown>

/** Replacing the backend address or transport does not change views or state. */
export function createScheduleApi(request: JsonRequest) {
  return {
    groups: () => request('/api/groups') as Promise<Catalog>,
    status: () => request('/api/status') as Promise<SyncStatus>,
    schedule: (groupId: string, window: Window, signal?: AbortSignal) =>
      request('/api/schedule', { query: { group_id: groupId, ...window }, signal }) as Promise<Schedule>,
  }
}
