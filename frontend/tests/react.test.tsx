import './setup-dom'
import { afterEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { act, cleanup, render, renderHook, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GroupPicker } from '../src/features/group-selection/ui/group-picker'
import { SchedulePanel } from '../src/widgets/schedule/ui/schedule-panel'
import { useCalendar } from '../src/widgets/schedule/model/use-calendar'
import type { Group, Schedule } from '../src/entities/schedule/model/types'

const groups: Group[] = [
  {
    id: 'a',
    name: 'МПИ-26-1-1',
    education_level: 'Магистратура',
    institutes: ['ИКН'],
    subgroups: [1, 2],
  },
  {
    id: 'b',
    name: 'БИВТ-26-1',
    education_level: 'Бакалавриат',
    institutes: ['ИКН'],
    subgroups: [],
  },
]
function schedule(id: string, start = '2026-09-07', end = '2026-09-13'): Schedule {
  return {
    revision: 'r',
    group: groups.find((g) => g.id === id)!,
    source: null,
    coverage: null,
    window: { start, end },
    available_dates: [start],
    lessons: [],
    warnings: [],
    stale: false,
    fetched_at: '2026-09-09T06:00:00Z',
  }
}
const originalFetch = globalThis.fetch
function mockCatalogThen(onSchedule: (url: URL, options?: RequestInit) => Promise<Response>) {
  globalThis.fetch = (async (input: string | URL | Request, options?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost')
    if (url.pathname === '/api/groups') return Response.json({ revision: 'r', groups })
    return onSchedule(url, options)
  }) as typeof fetch
}
afterEach(() => {
  cleanup()
  localStorage.clear()
  globalThis.fetch = originalFetch
})

test('keyboard group selection returns the ID, and filters narrow the catalog', async () => {
  const user = userEvent.setup()
  const selected: string[] = []
  render(
    <GroupPicker
      groups={groups}
      selected={null}
      onSelect={(id) => selected.push(id)}
      pending={false}
    />,
  )
  const input = screen.getByRole('combobox', { name: 'Найти учебную группу' })
  await user.type(input, 'мпи — 26')
  assert.equal(within(screen.getByRole('listbox')).getAllByRole('option').length, 1)
  await user.keyboard('{Enter}')
  assert.deepEqual(selected, ['a'])
  assert.equal(input.getAttribute('aria-expanded'), 'false')
  await user.click(screen.getByText('Уточнить поиск'))
  await user.selectOptions(screen.getByLabelText('Уровень образования'), 'Бакалавриат')
  await user.click(input)
  assert.ok(screen.getByRole('option', { name: 'БИВТ-26-1 Бакалавриат' }))
  await user.keyboard('{Escape}')
  assert.equal(input.getAttribute('aria-expanded'), 'false')
})

test('restores preferences and ignores a late response from the previous group', async () => {
  localStorage.setItem('misisync-group', 'a')
  localStorage.setItem('misisync-subgroup:a', '2')
  let resolveFirst!: (response: Response) => void
  let oldSignal: AbortSignal | null | undefined
  mockCatalogThen(async (url, options) => {
    if (url.searchParams.get('group_id') === 'a') {
      oldSignal = options?.signal
      return new Promise((resolve) => {
        resolveFirst = resolve
      })
    }
    return Response.json(schedule('b'))
  })
  const { result } = renderHook(() => useCalendar('2026-09-09'))
  await waitFor(() => assert.equal(result.current.group?.id, 'a'))
  assert.equal(result.current.subgroup, '2')
  await waitFor(() => assert.equal(typeof resolveFirst, 'function'))
  act(() => result.current.selectGroup('b'))
  assert.equal(Boolean(result.current.schedule), false)
  await waitFor(() => assert.equal(result.current.schedule?.group?.id, 'b'))
  assert.equal(oldSignal?.aborted, true)
  await act(async () => {
    resolveFirst(Response.json(schedule('a')))
  })
  assert.equal(result.current.schedule?.group?.id, 'b')
  assert.equal(localStorage.getItem('misisync-group'), 'b')
})

test('navigation clears the previous week, failed requests can be retried', async () => {
  localStorage.setItem('misisync-group', 'a')
  let fail = false
  const starts: string[] = []
  mockCatalogThen(async (url) => {
    const start = url.searchParams.get('start')!
    starts.push(start)
    return fail
      ? new Response('', { status: 502 })
      : Response.json(schedule('a', start, url.searchParams.get('end')!))
  })
  const { result } = renderHook(() => useCalendar('2026-09-09'))
  await waitFor(() => assert.equal(result.current.schedule?.window.start, '2026-09-07'))
  fail = true
  act(() => result.current.setWeekStart('2026-09-14'))
  assert.equal(Boolean(result.current.schedule), false)
  await waitFor(() => assert.ok(result.current.error))
  fail = false
  act(() => result.current.reload())
  await waitFor(() => assert.equal(result.current.schedule?.window.start, '2026-09-14'))
  assert.equal(result.current.error, null)
  assert.deepEqual(starts, ['2026-09-07', '2026-09-14', '2026-09-14'])
})

test('unmount aborts a pending schedule request', async () => {
  localStorage.setItem('misisync-group', 'a')
  let signal: AbortSignal | null | undefined
  mockCatalogThen(async (_url, options) => {
    signal = options?.signal
    return new Promise(() => {})
  })
  const { unmount } = renderHook(() => useCalendar('2026-09-09'))
  await waitFor(() => assert.ok(signal))
  unmount()
  assert.equal(signal?.aborted, true)
})

test('refresh information sits after the content and explains cached responses', async () => {
  const data = schedule('a')
  data.stale = true
  data.warnings = ['Показана последняя полученная версия.']
  let refreshes = 0
  render(
    <SchedulePanel
      group={groups[0]!}
      schedule={data}
      dates={[
        '2026-09-07',
        '2026-09-08',
        '2026-09-09',
        '2026-09-10',
        '2026-09-11',
        '2026-09-12',
        '2026-09-13',
      ]}
      weekday={0}
      subgroup="all"
      pending={false}
      error={null}
      catalogPending={false}
      onWeek={() => {}}
      onDay={() => {}}
      onSubgroup={() => {}}
      onRefresh={() => {
        refreshes++
      }}
    />,
  )
  const empty = screen.getByText('В расписании нет занятий')
  const refresh = screen.getByRole('button', { name: /Обновить/ })
  assert.ok(empty.compareDocumentPosition(refresh) & Node.DOCUMENT_POSITION_FOLLOWING)
  assert.ok(screen.getByText(/сохранённая версия/))
  const user = userEvent.setup()
  await user.click(screen.getByText('Данные расписания'))
  assert.ok(screen.getByText(/По умолчанию кэш действует 15 минут/))
  await user.click(refresh)
  assert.equal(refreshes, 1)
})
