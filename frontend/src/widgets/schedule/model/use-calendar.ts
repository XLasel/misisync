'use client'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { scheduleApi } from '../../../entities/schedule/api/schedule-api'
import type { Group, Schedule } from '../../../entities/schedule/model/types'
import { addDays, mondayOf } from '../../../shared/lib/calendar'
import { readPreference, savePreference } from '../../../shared/lib/preferences'

type Resource = {
  key: string
  data: Schedule | null
  phase: 'pending' | 'success' | 'error'
  error: string | null
}
const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'Не удалось загрузить данные.'

export function useCalendar(today: string) {
  const [catalog, setCatalog] = useState<Group[]>([])
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [catalogPending, setCatalogPending] = useState(true)
  const [catalogVersion, setCatalogVersion] = useState(0)
  const [groupId, setGroupId] = useState('')
  const [subgroup, setSubgroup] = useState('all')
  const [weekStart, setWeekStart] = useState(() => mondayOf(today))
  const [weekday, setWeekday] = useState(() => (new Date(`${today}T12:00:00Z`).getUTCDay() + 6) % 7)
  const [refreshVersion, setRefreshVersion] = useState(0)
  const [resource, setResource] = useState<Resource | null>(null)
  const window = useMemo(() => ({ start: weekStart, end: addDays(weekStart, 6) }), [weekStart])
  const dates = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)),
    [weekStart],
  )
  const group = catalog.find((item) => item.id === groupId) || null
  const key = JSON.stringify([group?.id, window])

  useEffect(() => {
    let active = true
    async function loadCatalog() {
      setCatalogPending(true)
      try {
        const result = await scheduleApi.groups()
        if (!active) return
        setCatalog(result.groups)
        setCatalogError(null)
        const saved = readPreference('misisync-group')
        if (result.groups.some((item) => item.id === saved)) {
          setGroupId(saved)
          setSubgroup(readPreference(`misisync-subgroup:${saved}`) || 'all')
        }
      } catch (error) {
        if (active) setCatalogError(errorMessage(error))
      } finally {
        if (active) setCatalogPending(false)
      }
    }
    void loadCatalog()
    return () => {
      active = false
    }
  }, [catalogVersion])

  useEffect(() => {
    if (!group) return
    const controller = new AbortController()
    let active = true
    async function loadSchedule() {
      setResource((previous) => ({
        key,
        data: previous?.key === key ? previous.data : null,
        phase: 'pending',
        error: null,
      }))
      try {
        const result = await scheduleApi.schedule(group!.id, window, controller.signal)
        if (active) setResource({ key, data: result, phase: 'success', error: null })
      } catch (error) {
        if (active)
          setResource((previous) => ({
            key,
            data: previous?.key === key ? previous.data : null,
            phase: 'error',
            error: errorMessage(error),
          }))
      }
    }
    void loadSchedule()
    return () => {
      active = false
      controller.abort()
    }
  }, [group, key, window, refreshVersion])

  const selectGroup = useCallback((id: string) => {
    setGroupId(id)
    setSubgroup(readPreference(`misisync-subgroup:${id}`) || 'all')
    savePreference('misisync-group', id)
  }, [])
  const selectSubgroup = (value: string) => {
    setSubgroup(value)
    savePreference(`misisync-subgroup:${groupId}`, value)
  }
  const reload = () => {
    if (catalogError) setCatalogVersion((value) => value + 1)
    setRefreshVersion((value) => value + 1)
  }
  // Never expose the previous group's/week's data, even before an effect runs.
  const current = resource?.key === key ? resource : null
  return {
    catalog,
    catalogError,
    catalogPending,
    group,
    subgroup,
    selectGroup,
    selectSubgroup,
    weekStart,
    setWeekStart,
    window,
    dates,
    weekday,
    setWeekday,
    reload,
    schedule: current?.data || null,
    error: current?.error || null,
    pending: Boolean(group) && (!current || current.phase === 'pending'),
  }
}
