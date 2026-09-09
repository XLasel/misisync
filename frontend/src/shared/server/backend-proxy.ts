const paths = new Set(['groups', 'schedule', 'status', 'health'])

/** Forward only the calendar API, without cookies, browser credentials or HTTP caching. */
export async function proxyBackend(
  request: Request,
  path: string[],
  fetcher: typeof fetch = fetch,
): Promise<Response> {
  if (request.method !== 'GET' || path.length !== 1 || !paths.has(path[0]!)) {
    return Response.json({ detail: 'Not found' }, { status: 404 })
  }
  const base = (process.env.API_BASE || 'http://127.0.0.1:8000').replace(/\/$/, '')
  const url = new URL(request.url)
  try {
    const upstream = await fetcher(`${base}/api/${path[0]}${url.search}`, {
      cache: 'no-store',
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(180_000)]),
      headers: { Accept: 'application/json' },
      redirect: 'error',
    })
    const headers = new Headers({
      'Content-Type': upstream.headers.get('content-type') || 'application/json',
      'Cache-Control': 'no-store',
    })
    const retry = upstream.headers.get('retry-after')
    if (retry) headers.set('Retry-After', retry)
    return new Response(upstream.body, { status: upstream.status, headers })
  } catch {
    return Response.json(
      { detail: 'Не удалось связаться с сервером расписания.' },
      { status: 502, headers: { 'Cache-Control': 'no-store' } },
    )
  }
}
