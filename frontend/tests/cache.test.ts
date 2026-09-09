/// <reference types="node" />
import test from 'node:test'
import assert from 'node:assert/strict'
import { ScheduleRateLimiter } from '../src/shared/server/rate-limit'

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
