import { proxyBackend } from '@/shared/server/backend-proxy'
export const dynamic = 'force-dynamic'
export async function GET(request: Request, context: { params: Promise<{ path: string[] }> }) {
  return proxyBackend(request, (await context.params).path)
}
