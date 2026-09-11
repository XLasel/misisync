import assert from 'node:assert/strict'
import test from 'node:test'

import { estimateWeekKind } from '../src/features/schedule-navigation/model/academic-week'

test('estimated academic weeks alternate around the confirmed reference, including previous weeks', () => {
  assert.equal(estimateWeekKind('2026-09-07'), 'lower')
  assert.equal(estimateWeekKind('2026-09-13'), 'lower')
  assert.equal(estimateWeekKind('2026-09-14'), 'upper')
  assert.equal(estimateWeekKind('2026-09-21'), 'lower')
  assert.equal(estimateWeekKind('2026-09-01'), 'upper')
  assert.equal(estimateWeekKind('2026-08-24'), 'lower')
})

test('estimated parity continues across year boundaries and supports changing the reference', () => {
  const reference = { date: '2026-12-28', kind: 'upper' as const }
  assert.equal(estimateWeekKind('2027-01-03', reference), 'upper')
  assert.equal(estimateWeekKind('2027-01-04', reference), 'lower')
  assert.equal(estimateWeekKind('2026-12-21', reference), 'lower')
})
