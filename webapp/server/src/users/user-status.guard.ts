import { ForbiddenException, Injectable, UnauthorizedException } from '@nestjs/common'
import type { CanActivate, ExecutionContext } from '@nestjs/common'
import { verifyInitData } from '../auth/telegram-auth.js'
import { UsersService } from './users.service.js'

@Injectable()
export class UserStatusGuard implements CanActivate {
  constructor(private readonly users: UsersService) {}

  async canActivate(context: ExecutionContext) {
    const req = context.switchToHttp().getRequest()
    const path = String(req.url || req.originalUrl || '')
    if (path.includes('/api/admin') || path.includes('/api/health') || path.includes('/api/me')) return true

    const initData = String(req.headers['x-telegram-init-data'] || '')
    if (!initData) return true
    const token = process.env.BOT_TOKEN?.trim()
    if (!token) throw new UnauthorizedException('BOT_TOKEN is not configured')
    const auth = verifyInitData(initData, token)
    if (!auth) throw new UnauthorizedException('Invalid or expired Telegram initData')

    const user = await this.users.findByTelegramId(String(auth.user.id))
    if (!user) return true
    const moderation = this.users.moderationSnapshot(user)
    if (moderation.status === 'blocked' || moderation.status === 'restricted') {
      throw new ForbiddenException({
        code: moderation.status === 'blocked' ? 'USER_BLOCKED' : 'USER_RESTRICTED',
        moderation,
      })
    }
    return true
  }
}
