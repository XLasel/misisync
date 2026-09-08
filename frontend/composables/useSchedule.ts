import { createScheduleApi } from '~/services/schedule-api'
import { addDays, mondayOf, moscowToday } from '~/utils/schedule'
import type { Schedule } from '~/types/schedule'

export function useSchedule() {
  const api = createScheduleApi((path, options) => $fetch(path, options))
  const { data: catalogData, error: catalogError, refresh: refreshCatalog } = useAsyncData('groups', api.groups, { default: () => ({ revision: null, groups: [] }) })
  const catalog = computed(() => catalogData.value.groups)
  const group = ref('')
  const weekStart = ref(mondayOf(moscowToday()))
  const weekEnd = computed(() => addDays(weekStart.value, 6))
  const weekDates = computed(() => Array.from({ length: 7 }, (_, i) => addDays(weekStart.value, i)))
  const schedule = ref<Schedule | null>(null)
  const scheduleError = ref<unknown>(null)
  const loading = ref<'idle' | 'pending' | 'success' | 'error'>('idle')
  let controller: AbortController | undefined
  let requestId = 0

  async function refreshSchedule() {
    const current = ++requestId
    controller?.abort()
    controller = new AbortController()
    schedule.value = null
    scheduleError.value = null
    if (!group.value) { loading.value = 'idle'; return }
    loading.value = 'pending'
    try {
      const result = await api.schedule(group.value, { start: weekStart.value, end: weekEnd.value }, controller.signal)
      if (current !== requestId) return
      schedule.value = result
      loading.value = 'success'
    } catch (error) {
      if (current !== requestId) return
      scheduleError.value = error
      loading.value = 'error'
    }
  }
  watch([group, weekStart], refreshSchedule)
  async function reload() {
    await refreshCatalog()
    await refreshSchedule()
  }
  return { catalog, catalogError, group, weekStart, weekEnd, weekDates, schedule, scheduleError, loading, reload }
}
