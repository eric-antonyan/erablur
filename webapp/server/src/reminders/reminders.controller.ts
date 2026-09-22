import { Body, Controller, Delete, Get, Header, Param, Put, Req, UseGuards } from '@nestjs/common'
import { TelegramAuthGuard } from '../auth/telegram-auth.js'
import { RemindersService } from './reminders.service.js'

@Controller('reminders')
@UseGuards(TelegramAuthGuard)
export class RemindersController {
  constructor(private readonly service: RemindersService) {}

  @Get()
  @Header('Cache-Control', 'private, no-store')
  list(@Req() req: any) { return this.service.listForUser(String(req.telegram.user.id)) }

  @Get('event/:eventId')
  @Header('Cache-Control', 'private, no-store')
  event(@Req() req: any, @Param('eventId') eventId: string) {
    return this.service.getForEvent(String(req.telegram.user.id), eventId)
  }

  @Put('event/:eventId')
  save(@Req() req: any, @Param('eventId') eventId: string, @Body() body: any) {
    return this.service.upsert(req.telegram.user, eventId, body)
  }

  @Delete('event/:eventId')
  cancel(@Req() req: any, @Param('eventId') eventId: string) {
    return this.service.cancel(String(req.telegram.user.id), eventId)
  }
}
