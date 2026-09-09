import test from 'node:test'
import assert from 'node:assert/strict'
import { proxyBackend } from '../src/shared/server/backend-proxy'
import { clientIp, isScheduleRequest } from '../src/shared/server/rate-limit'

test('forwarded IP cannot bypass the default socket-based quota', () => {
  assert.equal(clientIp('1.2.3.4', 'spoofed, 5.6.7.8', false), '1.2.3.4')
  assert.equal(clientIp('1.2.3.4', '5.6.7.8, 10.0.0.1', true), '5.6.7.8')
  assert.equal(clientIp('1.2.3.4', undefined, true), '1.2.3.4')
})

test('proxy preserves query, response status and retry headers, without forwarding credentials', async () => {
  let called = false
  const response = await proxyBackend(
    new Request('http://localhost/api/schedule?group_id=a&start=2026-09-07', {
      headers: { Cookie: 'private=value', Authorization: 'secret' },
    }),
    ['schedule'],
    (async (input, options) => {
      called = true
      const url = new URL(String(input))
      assert.equal(url.pathname, '/api/schedule')
      assert.equal(url.searchParams.get('group_id'), 'a')
      assert.equal(options?.cache, 'no-store')
      assert.deepEqual(options?.headers, { Accept: 'application/json' })
      return Response.json({ detail: 'busy' }, { status: 503, headers: { 'Retry-After': '5' } })
    }) as typeof fetch,
  )
  assert.equal(called, true)
  assert.equal(response.status, 503)
  assert.equal(response.headers.get('retry-after'), '5')
  assert.equal(response.headers.get('cache-control'), 'no-store')
  assert.deepEqual(await response.json(), { detail: 'busy' })
})

test('proxy rejects arbitrary paths and handles an unreachable backend', async () => {
  const fetcher = (async () => {
    throw new Error('offline')
  }) as typeof fetch
  assert.equal(
    (await proxyBackend(new Request('http://localhost/api/other'), ['other'], fetcher)).status,
    404,
  )
  assert.equal(
    (
      await proxyBackend(
        new Request('http://localhost/api/health', { method: 'POST' }),
        ['health'],
        fetcher,
      )
    ).status,
    404,
  )
  assert.equal(
    (await proxyBackend(new Request('http://localhost/api/health'), ['health'], fetcher)).status,
    502,
  )
})

test('encoded API routes cannot bypass the schedule limiter', () => {
  for (const path of [
    '/api/schedule',
    '/api/schedule/?start=x',
    '/api/%73chedule',
    '/api/%73chedule/',
  ]) {
    assert.equal(isScheduleRequest('GET', path), true)
  }
  assert.equal(isScheduleRequest('GET', '/api/groups'), false)
  assert.equal(isScheduleRequest('GET', '/api/%'), false)
})
