/// <reference types="node" />
import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizeGroupSearch, scheduleCards } from '../utils/schedule.ts'
import type { Lesson } from '../utils/schedule.ts'

const base: Lesson = { id: 'common', group_name: 'БИВТ-26-1', weekday: 0, start_time: '09:00', end_time: '10:35', subject: 'Математика', lesson_type: 'Лекция', teacher: 'Иванов И. И.', room: 'Б-101', subgroup: '', subgroup_ids: [], week_pattern: 'all', notes: '', raw_text: 'original', source_url: '', source_sheet: '', source_cell: '' }

test('subgroup filter keeps common and shared lessons, excludes other subgroups', () => {
  const rows = [base, { ...base, id: 'one', subject: 'Практика 1', subgroup: '1', subgroup_ids: [1] },
    { ...base, id: 'two', subject: 'Практика 2', subgroup: '2', subgroup_ids: [2] },
    { ...base, id: 'shared', subject: 'Практика 1,3', subgroup: '1, 3', subgroup_ids: [1, 3] }]
  assert.deepEqual(scheduleCards(rows, 'all', '1').map(x => x.id).sort(), ['common', 'one', 'shared'])
  assert.deepEqual(scheduleCards(rows, 'all', '3').map(x => x.id).sort(), ['common', 'shared'])
})

test('one card for an identical lesson in two lanes, both originals retained', () => {
  const rows = [{ ...base, id: 'one', subgroup: '1 подгруппа', subgroup_ids: [1] }, { ...base, id: 'two', subgroup: '2 подгруппа', subgroup_ids: [2] }]
  const cards = scheduleCards(rows, 'all', 'all')
  assert.equal(cards.length, 1)
  assert.deepEqual(cards[0]!.subgroup_ids, [1, 2])
  assert.equal(cards[0]!.originals.length, 2)
  assert.deepEqual(rows[0]!.subgroup_ids, [1])
})

test('different rooms and week conditions are never merged', () => {
  const rows = [base, { ...base, id: 'room', room: 'Б-202' }, { ...base, id: 'week', week_pattern: 'even' }]
  assert.equal(scheduleCards(rows, 'all', 'all').length, 3)
  assert.equal(scheduleCards(rows, 'odd', 'all').length, 2)
})

test('search tolerates spaces, case, and alternate dashes', () => {
  assert.equal(normalizeGroupSearch(' бивт — 26–1 '), 'БИВТ-26-1')
})
