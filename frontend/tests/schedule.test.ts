/// <reference types="node" />
import test from 'node:test'
import assert from 'node:assert/strict'
import { scheduleCards } from '../src/entities/schedule/model/selectors'
import { normalizeGroupSearch } from '../src/shared/lib/search'
import { addDays, mondayOf } from '../src/shared/lib/calendar'
import { createScheduleApi } from '../src/entities/schedule/api/schedule-api'
import type { Lesson } from '../src/entities/schedule/model/types'

const base: Lesson = {
  id: 'common',
  group_id: 'БИВТ-26-1',
  date: '2026-09-07',
  start_time: '09:00',
  end_time: '10:35',
  subject: 'Математика',
  lesson_type: 'Лекция',
  teachers: ['Иванов И. И.'],
  rooms: ['Б-101'],
  subgroup_label: '',
  subgroup_ids: [],
  notes: [],
  warnings: [],
  evidence: [{ url: '', label: 'cell', raw_text: 'original', external_id: null }],
}

test('subgroup filter retains unspecified and shared classes', () => {
  const rows = [
    base,
    { ...base, id: 'one', subject: 'Практика 1', subgroup_ids: [1] },
    { ...base, id: 'two', subject: 'Практика 2', subgroup_ids: [2] },
    { ...base, id: 'shared', subject: 'Практика 1,3', subgroup_ids: [1, 3] },
  ]
  assert.deepEqual(
    scheduleCards(rows, '1')
      .map((x) => x.id)
      .sort(),
    ['common', 'one', 'shared'],
  )
  assert.deepEqual(
    scheduleCards(rows, '3')
      .map((x) => x.id)
      .sort(),
    ['common', 'shared'],
  )
})

test('identical subgroup classes combine without mutating originals', () => {
  const rows = [
    { ...base, id: 'one', subgroup_ids: [1] },
    { ...base, id: 'two', subgroup_ids: [2] },
  ]
  const cards = scheduleCards(rows, 'all')
  assert.equal(cards.length, 1)
  assert.deepEqual(cards[0]!.subgroup_ids, [1, 2])
  assert.equal(cards[0]!.evidence.length, 2)
  assert.deepEqual(rows[0]!.subgroup_ids, [1])
  assert.equal(rows[0]!.evidence.length, 1)
})

test('different dates, rooms, types and ambiguous times survive grouping', () => {
  const rows = [
    base,
    { ...base, id: 'room', rooms: ['Б-202'] },
    { ...base, id: 'date', date: '2026-09-14' },
    { ...base, id: 'type', lesson_type: 'Практика' },
    {
      ...base,
      id: 'repeat',
      start_time: '10:50',
      end_time: '12:25',
      warnings: ['Повтор в источнике'],
    },
  ]
  assert.equal(scheduleCards(rows, 'all').length, 5)
})

test('unknown time sorts after known times without a fabricated default', () => {
  const unknown = { ...base, id: 'unknown', start_time: null, end_time: null }
  assert.deepEqual(
    scheduleCards([unknown, base], 'all').map((x) => x.id),
    ['common', 'unknown'],
  )
})

test('calendar navigation crosses year and month boundaries using calendar dates', () => {
  assert.equal(mondayOf('2027-01-01'), '2026-12-28')
  assert.equal(addDays('2026-09-28', 6), '2026-10-04')
  assert.equal(addDays('2026-12-28', 7), '2027-01-04')
})

test('frontend gateway uses one contract independent of provider', async () => {
  const requests: unknown[] = []
  const api = createScheduleApi(async (path, options) => {
    requests.push([path, options])
    return {}
  })
  const signal = new AbortController().signal
  await api.groups()
  await api.schedule('МПИ-26-1-1', { start: '2026-09-07', end: '2026-09-13' }, signal)
  assert.deepEqual(requests, [
    ['/api/groups', undefined],
    [
      '/api/schedule',
      {
        query: { group_id: 'МПИ-26-1-1', start: '2026-09-07', end: '2026-09-13' },
        signal,
      },
    ],
  ])
})

test('search normalizes spaces, case and dashes', () => {
  assert.equal(normalizeGroupSearch(' бивт — 26–1 '), 'БИВТ-26-1')
})
