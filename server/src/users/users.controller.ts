import { Body, Controller, Delete, Get, Header, Post, Req, UseGuards } from '@nestjs/common'
import { TelegramAuthGuard } from '../auth/telegram-auth.js'
import { UsersService } from './users.service.js'

@Controller()
@UseGuards(TelegramAuthGuard)
export class UsersController {
  constructor(private readonly service: UsersService) {}

  @Get('me')
  @Header('Cache-Control', 'private, no-store')
  me(@Req() req: any) {
    return this.service.me(req.telegram.user)
  }

  @Post('history')
  history(@Req() req: any, @Body() body: { query?: string; heroId?: string; heroName?: string }) {
    return this.service.addHistory(req.telegram.user, body)
  }

  @Delete('history')
  clear(@Req() req: any) {
    return this.service.clearHistory(req.telegram.user)
  }
}
