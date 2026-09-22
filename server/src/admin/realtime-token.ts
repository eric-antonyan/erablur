import { createHmac, randomUUID, timingSafeEqual } from 'node:crypto'

export const ADMIN_RT_SCOPE = 'admin-realtime'

function secret() {
  const value = process.env.ADMIN_SESSION_SECRET?.trim()
  if (!value || value.length < 24) throw new Error('ADMIN_SESSION_SECRET must be at least 24 characters')
  return value
}

function safeEqual(a: string, b: string) {
  const aa = Buffer.from(a)
  const bb = Buffer.from(b)
  if (aa.length !== bb.length) return false
  return timingSafeEqual(aa, bb)
}

export function createAdminRealtimeToken(ttlSeconds = 12 * 60 * 60) {
  const payload = Buffer.from(JSON.stringify({
    scope: ADMIN_RT_SCOPE,
    exp: Math.floor(Date.now() / 1000) + ttlSeconds,
    nonce: randomUUID(),
  })).toString('base64url')
  const signature = createHmac('sha256', secret()).update(payload).digest('base64url')
  return `${payload}.${signature}`
}

export function verifyAdminRealtimeToken(token: string) {
  const [payload, signature] = String(token || '').split('.')
  if (!payload || !signature) return false
  const expected = createHmac('sha256', secret()).update(payload).digest('base64url')
  if (!safeEqual(signature, expected)) return false
  try {
    const data = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'))
    return data?.scope === ADMIN_RT_SCOPE && Number(data?.exp) > Math.floor(Date.now() / 1000)
  } catch {
    return false
  }
}
