/** In-process sliding window; bounded even when visitors use many distinct IPs. */
export class ScheduleRateLimiter {
  private visitors = new Map<string, number[]>()
  private readonly capacity: number
  private readonly clock: () => number
  constructor(capacity = 4096, clock = () => performance.now()) {
    this.capacity = capacity
    this.clock = clock
  }

  retryAfter(ip: string, limit: number): number {
    const now = this.clock()
    for (const [key, times] of this.visitors) {
      while (times.length && times[0]! <= now - 60_000) times.shift()
      if (!times.length) this.visitors.delete(key)
    }
    const times = this.visitors.get(ip) || []
    if (times.length >= limit) return Math.max(1, Math.ceil((times[0]! + 60_000 - now) / 1000))
    // Do not evict a live limit: that would let another IP reset existing visitors' quotas.
    if (!times.length && this.visitors.size >= this.capacity) return 60
    times.push(now)
    this.visitors.set(ip, times)
    return 0
  }
}

export function clientIp(
  remote: string | undefined,
  forwarded: string | string[] | undefined,
  trustProxy: boolean,
): string {
  const header = Array.isArray(forwarded) ? forwarded[0] : forwarded
  return (trustProxy ? header?.split(',')[0]?.trim() : undefined) || remote || 'unknown'
}

/** Match the decoded route, including percent-encoded names and trailing slashes. */
export function isScheduleRequest(method: string | undefined, url: string | undefined): boolean {
  if (method !== 'GET' || !url) return false
  try {
    const path = decodeURIComponent(new URL(url, 'http://localhost').pathname).replace(/\/+$/, '')
    return path === '/api/schedule'
  } catch {
    return false
  }
}
