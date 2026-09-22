import { Controller, Get, Headers, Query, UnauthorizedException } from '@nestjs/common'
import { timingSafeEqual } from 'node:crypto'
import { RemindersService } from './reminders.service.js'

function sameSecret(a: string, b: string) {
  const aa = Buffer.from(a)
  const bb = Buffer.from(b)
  return aa.length === bb.length && timingSafeEqual(aa, bb)
}

@Controller('tasks')
export class TasksController {
  constructor(private readonly reminders: RemindersService) {}

  @Get('event-reminders')
  run(@Headers('authorization') authorization?: string, @Query('limit') limit?: string) {
    const secret = process.env.CRON_SECRET?.trim()
    if (!secret) throw new UnauthorizedException('CRON_SECRET is not configured')
    const expected = `Bearer ${secret}`
    if (!authorization || !sameSecret(authorization, expected)) throw new UnauthorizedException('Invalid cron authorization')
    return this.reminders.processDue(Number(limit) || 100)
  }
}
