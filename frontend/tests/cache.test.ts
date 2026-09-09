/// <reference types="node" />
import test from 'node:test'
import assert from 'node:assert/strict'
import { ScheduleRateLimiter } from '../server/utils/rate-limit.ts'
import { matchesSchedule } from '../utils/schedule.ts'
import type { Schedule } from '../types/schedule.ts'

test('each visitor has a separate quota, which recovers as requests expire', () => {
  let now = 0
  const limiter = new ScheduleRateLimiter(3, () => now)
  assert.equal(limiter.retryAfter('alice', 2), 0)
  now = 1000
  assert.equal(limiter.retryAfter('alice', 2), 0)
  assert.equal(limiter.retryAfter('alice', 2), 59)
  assert.equal(limiter.retryAfter('bob', 2), 0)
  now = 60_000
  assert.equal(limiter.retryAfter('alice', 2), 0)
  assert.equal(limiter.retryAfter('alice', 2), 1)
})

test('bounded visitor storage cannot reset another visitor quota', () => {
  let now = 0
  const limiter = new ScheduleRateLimiter(1, () => now)
  assert.equal(limiter.retryAfter('alice', 1), 0)
  assert.equal(limiter.retryAfter('bob', 1), 60)
  assert.equal(limiter.retryAfter('alice', 1), 60)
  now = 60_000
  assert.equal(limiter.retryAfter('bob', 1), 0)
})

test('previous schedule is reusable only for the same group and window', () => {
  const window = { start: '2026-09-07', end: '2026-09-13' }
  const schedule: Schedule = { group: { id: 'one', name: 'First', institutes: [], education_level: '', subgroups: [] },
    revision: null, source: null, coverage: null, window, lessons: [], available_dates: [], warnings: [], fetched_at: null, stale: false }
  assert.equal(matchesSchedule(schedule, 'one', window), true)
  assert.equal(matchesSchedule(schedule, 'two', window), false)
  assert.equal(matchesSchedule(schedule, 'one', { start: '2026-09-14', end: '2026-09-20' }), false)
  assert.equal(matchesSchedule(null, 'one', window), false)
})
