import { Injectable, UnauthorizedException } from '@nestjs/common'
import type { CanActivate, ExecutionContext } from '@nestjs/common'
import { createHmac, timingSafeEqual } from 'node:crypto'

export type TelegramMiniAppUser = {
  id: number
  first_name?: string
  last_name?: string
  username?: string
  language_code?: string
  photo_url?: string
}

export type TelegramAuthData = {
  user: TelegramMiniAppUser
  authDate: number
  queryId?: string
}

export function verifyInitData(initData: string, botToken: string): TelegramAuthData | null {
  const params = new URLSearchParams(initData)
  const hash = params.get('hash')
  if (!hash || !/^[a-f0-9]{64}$/i.test(hash)) return null
  params.delete('hash')

  const dataCheckString = [...params.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}=${value}`)
    .join('\n')

  const secret = createHmac('sha256', 'WebAppData').update(botToken).digest()
  const calculated = createHmac('sha256', secret).update(dataCheckString).digest('hex')
  const expected = Buffer.from(hash, 'hex')
  const actual = Buffer.from(calculated, 'hex')
  if (expected.length !== actual.length || !timingSafeEqual(expected, actual)) return null

  const authDate = Number(params.get('auth_date') || 0)
  if (!authDate || Math.abs(Date.now() / 1000 - authDate) > 24 * 60 * 60) return null

  try {
    const userRaw = params.get('user')
    const user = userRaw ? JSON.parse(userRaw) : null
    if (!user?.id) return null
    return { user, authDate, queryId: params.get('query_id') || undefined }
  } catch {
    return null
  }
}

@Injectable()
export class TelegramAuthGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const req = context.switchToHttp().getRequest()
    const initData = String(req.headers['x-telegram-init-data'] || '')
    const token = process.env.BOT_TOKEN?.trim()
    if (!token) throw new UnauthorizedException('BOT_TOKEN is not configured')
    if (!initData) throw new UnauthorizedException('Telegram initData is missing')

    const auth = verifyInitData(initData, token)
    if (!auth) throw new UnauthorizedException('Invalid or expired Telegram initData')
    req.telegram = auth
    return true
  }
}
