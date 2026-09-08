export default defineEventHandler(async (event) => {
  const path = getRouterParam(event, 'path') || ''
  if (!['groups', 'catalog', 'schedule', 'status', 'health'].includes(path) || event.method !== 'GET') {
    throw createError({ statusCode: 404, statusMessage: 'Not found' })
  }
  const base = useRuntimeConfig(event).apiBase.replace(/\/$/, '')
  return proxyRequest(event, `${base}/api/${path}${getRequestURL(event).search}`)
})
