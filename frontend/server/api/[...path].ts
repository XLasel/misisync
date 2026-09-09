import { ScheduleRateLimiter } from '../utils/rate-limit'

const limiter = new ScheduleRateLimiter()

export default defineEventHandler(async (event) => {
  const path = getRouterParam(event, 'path') || ''
  if (!['groups', 'schedule', 'status', 'health'].includes(path) || event.method !== 'GET') {
    throw createError({ statusCode: 404, statusMessage: 'Not found' })
  }
  const config = useRuntimeConfig(event)
  if (path === 'schedule') {
    const configured = Number(config.scheduleRateLimitPerMinute)
    const limit = Number.isFinite(configured) && configured >= 1 ? Math.floor(configured) : 60
    const ip = getRequestIP(event, { xForwardedFor: String(config.trustProxy) === 'true' }) || 'unknown'
    const retryAfter = limiter.retryAfter(ip, limit)
    if (retryAfter) {
      setResponseHeader(event, 'Retry-After', retryAfter)
      throw createError({ statusCode: 429, statusMessage: 'Too many schedule requests' })
    }
  }
  const base = config.apiBase.replace(/\/$/, '')
  return proxyRequest(event, `${base}/api/${path}${getRequestURL(event).search}`)
})
