export async function requestJson(
  path: string,
  options?: { query?: Record<string, string>; signal?: AbortSignal },
): Promise<unknown> {
  const query = options?.query ? `?${new URLSearchParams(options.query)}` : ''
  const response = await fetch(`${path}${query}`, { signal: options?.signal, cache: 'no-store' })
  if (!response.ok) {
    const message =
      response.status === 429
        ? 'Слишком много запросов. Подожди минуту и попробуй снова.'
        : response.status === 503
          ? 'Источник занят. Попробуй через несколько секунд.'
          : 'Не удалось получить данные. Попробуй ещё раз.'
    throw new Error(message)
  }
  return response.json()
}
