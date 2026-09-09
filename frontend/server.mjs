import { createServer } from 'node:http'
import next from 'next'
import { ScheduleRateLimiter, clientIp, isScheduleRequest } from './src/shared/server/rate-limit.ts'

// Read the socket before Next converts the request to the Web Request API.
// Client-supplied forwarding headers are ignored unless a trusted ingress is configured.
const dev = process.argv.includes('--dev')
const portIndex = process.argv.indexOf('--port')
const port = Number(portIndex >= 0 ? process.argv[portIndex + 1] : process.env.PORT || 3000)
const hostname = process.env.HOST || '0.0.0.0'
const app = next({ dev, hostname, port })
const handle = app.getRequestHandler()
const limiter = new ScheduleRateLimiter()
const configuredLimit = Number(process.env.SCHEDULE_RATE_LIMIT_PER_MINUTE || 60)
if (!Number.isInteger(configuredLimit) || configuredLimit < 1)
  throw new Error('Invalid SCHEDULE_RATE_LIMIT_PER_MINUTE')
await app.prepare()
const server = createServer(async (req, res) => {
  try {
    if (isScheduleRequest(req.method, req.url)) {
      const retryAfter = limiter.retryAfter(
        clientIp(
          req.socket.remoteAddress,
          req.headers['x-forwarded-for'],
          process.env.TRUST_PROXY === 'true',
        ),
        configuredLimit,
      )
      if (retryAfter) {
        res.writeHead(429, {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-store',
          'Retry-After': String(retryAfter),
        })
        res.end(JSON.stringify({ detail: 'Слишком много запросов. Попробуй через минуту.' }))
        return
      }
    }
    await handle(req, res)
  } catch (error) {
    console.error('Request failed', error)
    if (!res.headersSent) res.writeHead(500)
    res.end()
  }
})
server.listen(port, hostname, () => console.log(`Misisync: http://localhost:${port}`))
for (const signal of ['SIGTERM', 'SIGINT'])
  process.once(signal, () => {
    server.close(async () => {
      await app.close()
      process.exit(0)
    })
    setTimeout(() => process.exit(0), 5000).unref()
  })
