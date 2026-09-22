import { ForbiddenException, Injectable, UnauthorizedException } from '@nestjs/common'
import { createHash, createHmac, timingSafeEqual } from 'node:crypto'
import type { Request } from 'express'

const COOKIE = 'hh_admin'
const TTL_SECONDS = 12 * 60 * 60

type Attempt = { count: number; resetAt: number }
export type AdminSession = {
  exp: number
  scope: 'admin-console'
  role: 'owner' | 'admin'
  actor: string
  telegram_id?: string
  auth: 'telegram' | 'password'
}

function base64url(value: string) { return Buffer.from(value).toString('base64url') }
function safeEqual(a: string, b: string) {
  const aa = Buffer.from(a), bb = Buffer.from(b)
  if (aa.length !== bb.length) return false
  return timingSafeEqual(aa, bb)
}

@Injectable()
export class AdminAuthService {
  private readonly attempts = new Map<string, Attempt>()

  private secret() {
    const value = process.env.ADMIN_SESSION_SECRET?.trim()
    if (!value || value.length < 24) throw new Error('ADMIN_SESSION_SECRET must be at least 24 characters')
    return value
  }

  verifyPassword(password: string, ip = 'unknown') {
    const now = Date.now()
    const attempt = this.attempts.get(ip)
    if (attempt && attempt.resetAt > now && attempt.count >= 8) return false
    if (attempt && attempt.resetAt <= now) this.attempts.delete(ip)
    const candidate = String(password || '')
    const expectedHash = process.env.ADMIN_PASSWORD_SHA256?.trim().toLowerCase()
    const plain = process.env.ADMIN_PASSWORD || ''
    const ok = expectedHash
      ? safeEqual(createHash('sha256').update(candidate).digest('hex'), expectedHash)
      : Boolean(plain) && safeEqual(candidate, plain)
    if (ok) { this.attempts.delete(ip); return true }
    const current = this.attempts.get(ip)
    this.attempts.set(ip, { count: (current?.resetAt && current.resetAt > now ? current.count : 0) + 1, resetAt: now + 10 * 60 * 1000 })
    return false
  }

  createToken(input: Omit<AdminSession, 'exp' | 'scope'>) {
    const payload: AdminSession = { exp: Math.floor(Date.now() / 1000) + TTL_SECONDS, scope: 'admin-console', ...input }
    const encoded = base64url(JSON.stringify(payload))
    const signature = createHmac('sha256', this.secret()).update(encoded).digest('base64url')
    return `${encoded}.${signature}`
  }

  cookie(token: string) {
    return `${COOKIE}=${token}; Path=/; HttpOnly; ${process.env.NODE_ENV === 'production' ? 'Secure; ' : ''}SameSite=Lax; Max-Age=${TTL_SECONDS}`
  }
  clearCookie() { return `${COOKIE}=; Path=/; HttpOnly; ${process.env.NODE_ENV === 'production' ? 'Secure; ' : ''}SameSite=Lax; Max-Age=0` }

  verifyRequest(req: Request): AdminSession | null {
    const raw = req.headers.cookie || ''
    const token = raw.split(';').map((part) => part.trim()).find((part) => part.startsWith(`${COOKIE}=`))?.slice(COOKIE.length + 1)
    if (!token) return null
    const [encoded, signature] = token.split('.')
    if (!encoded || !signature) return null
    const expected = createHmac('sha256', this.secret()).update(encoded).digest('base64url')
    if (!safeEqual(signature, expected)) return null
    try {
      const data = JSON.parse(Buffer.from(encoded, 'base64url').toString('utf8')) as AdminSession
      if (data.scope !== 'admin-console' || Number(data.exp) <= Math.floor(Date.now() / 1000)) return null
      if (!['owner', 'admin'].includes(data.role)) return null
      return data
    } catch { return null }
  }

  assert(req: Request) {
    const session = this.verifyRequest(req)
    if (!session) throw new UnauthorizedException('Admin session required')
    return session
  }
  assertOwner(req: Request) {
    const session = this.assert(req)
    if (session.role !== 'owner') throw new ForbiddenException('Owner access required')
    return session
  }
}
