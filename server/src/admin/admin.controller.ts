import { Body, Controller, Delete, Get, Header, Param, Patch, Post, Query, Req, Res, UnauthorizedException } from '@nestjs/common'
import type { Request, Response } from 'express'
import { EventsService } from '../events/events.service.js'
import { UsersService } from '../users/users.service.js'
import { RemindersService } from '../reminders/reminders.service.js'
import { BroadcastsService } from '../broadcasts/broadcasts.service.js'
import { verifyInitData } from '../auth/telegram-auth.js'
import { AdminAuthService } from './admin-auth.service.js'
import { AdminsService } from './admins.service.js'
import { createAdminRealtimeToken } from './realtime-token.js'

@Controller('admin')
export class AdminController {
  constructor(
    private readonly auth: AdminAuthService,
    private readonly admins: AdminsService,
    private readonly events: EventsService,
    private readonly users: UsersService,
    private readonly reminders: RemindersService,
    private readonly broadcasts: BroadcastsService,
  ) {}

  @Get('session')
  @Header('Cache-Control', 'private, no-store')
  session(@Req() req: Request) {
    const session = this.auth.verifyRequest(req)
    return { authenticated: Boolean(session), session: session ? { role: session.role, actor: session.actor, telegram_id: session.telegram_id || '', auth: session.auth } : null, owner_id: this.admins.ownerId() }
  }

  @Post('login')
  login(@Req() req: Request, @Res({ passthrough: true }) res: Response, @Body() body: { password?: string }) {
    const forwarded = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim()
    const ip = forwarded || req.ip || 'unknown'
    if (!this.auth.verifyPassword(body?.password || '', ip)) throw new UnauthorizedException('Invalid password')
    const token = this.auth.createToken({ role: 'admin', actor: 'password-admin', auth: 'password' })
    res.setHeader('Set-Cookie', this.auth.cookie(token))
    return { ok: true, expiresIn: 12 * 60 * 60, role: 'admin' }
  }

  @Post('telegram-login')
  async telegramLogin(@Req() req: Request, @Res({ passthrough: true }) res: Response) {
    const token = process.env.BOT_TOKEN?.trim()
    if (!token) throw new UnauthorizedException('BOT_TOKEN is not configured')
    const initData = String(req.headers['x-telegram-init-data'] || '')
    const verified = initData ? verifyInitData(initData, token) : null
    if (!verified) throw new UnauthorizedException('Valid Telegram Mini App session required')
    const access = await this.admins.resolve(String(verified.user.id))
    if (!access) throw new UnauthorizedException('This Telegram account is not an admin')
    const sessionToken = this.auth.createToken({ role: access.role, actor: `telegram:${access.telegram_id}`, telegram_id: access.telegram_id, auth: 'telegram' })
    res.setHeader('Set-Cookie', this.auth.cookie(sessionToken))
    return { ok: true, role: access.role, telegram_id: access.telegram_id, expiresIn: 12 * 60 * 60 }
  }

  @Post('logout')
  logout(@Res({ passthrough: true }) res: Response) {
    res.setHeader('Set-Cookie', this.auth.clearCookie())
    return { ok: true }
  }

  @Get('realtime-token')
  realtimeToken(@Req() req: Request) {
    this.auth.assert(req)
    return { token: createAdminRealtimeToken(), expiresIn: 12 * 60 * 60 }
  }

  @Get('admins')
  @Header('Cache-Control', 'private, no-store')
  listAdmins(@Req() req: Request) { this.auth.assertOwner(req); return this.admins.list() }

  @Post('admins')
  addAdmin(@Req() req: Request, @Body() body: any) {
    const session = this.auth.assertOwner(req)
    return this.admins.add(body, session.actor)
  }

  @Delete('admins/:telegramId')
  removeAdmin(@Req() req: Request, @Param('telegramId') telegramId: string) {
    this.auth.assertOwner(req)
    return this.admins.remove(telegramId)
  }

  @Get('stats')
  @Header('Cache-Control', 'private, no-store')
  async stats(@Req() req: Request) {
    this.auth.assert(req)
    const [users, events, reminders, broadcasts] = await Promise.all([this.users.adminStats(), this.events.listAdmin(), this.reminders.adminStats(), this.broadcasts.stats()])
    return {
      users,
      events: { total: events.length, published: events.filter((item: any) => item.published !== false).length, annual: events.filter((item: any) => item.annual !== false).length },
      reminders,
      broadcasts,
    }
  }

  @Get('users')
  @Header('Cache-Control', 'private, no-store')
  listUsers(@Req() req: Request, @Query('q') q?: string, @Query('status') status?: string, @Query('page') page?: string, @Query('limit') limit?: string) {
    this.auth.assert(req)
    return this.users.adminList({ q, status, page: Number(page), limit: Number(limit) })
  }

  @Get('users/:id')
  @Header('Cache-Control', 'private, no-store')
  getUser(@Req() req: Request, @Param('id') id: string) { this.auth.assert(req); return this.users.adminGet(id) }

  @Patch('users/:id/moderation')
  moderateUser(@Req() req: Request, @Param('id') id: string, @Body() body: any) {
    const session = this.auth.assert(req)
    return this.users.moderate(id, body, session.actor)
  }

  @Delete('users/:id/history')
  clearUserHistory(@Req() req: Request, @Param('id') id: string) { this.auth.assert(req); return this.users.clearHistoryAdmin(id) }

  @Get('reminders')
  @Header('Cache-Control', 'private, no-store')
  listReminders(@Req() req: Request, @Query('status') status?: string, @Query('limit') limit?: string) {
    this.auth.assert(req)
    return this.reminders.adminList({ status, limit: Number(limit) })
  }

  @Get('reminder-deliveries')
  @Header('Cache-Control', 'private, no-store')
  reminderDeliveries(@Req() req: Request, @Query('limit') limit?: string) { this.auth.assert(req); return this.reminders.adminDeliveries(Number(limit) || 80) }

  @Post('reminders/run')
  runReminders(@Req() req: Request) { this.auth.assert(req); return this.reminders.processDue(150) }

  @Delete('reminders/:id')
  cancelReminder(@Req() req: Request, @Param('id') id: string) { this.auth.assert(req); return this.reminders.adminCancel(id) }

  @Get('broadcasts')
  @Header('Cache-Control', 'private, no-store')
  broadcastsList(@Req() req: Request, @Query('limit') limit?: string) { this.auth.assert(req); return this.broadcasts.list(Number(limit) || 80) }

  @Get('broadcasts/:id/deliveries')
  @Header('Cache-Control', 'private, no-store')
  broadcastDeliveries(@Req() req: Request, @Param('id') id: string, @Query('limit') limit?: string) { this.auth.assert(req); return this.broadcasts.deliveries(id, Number(limit) || 100) }

  @Post('broadcasts')
  createBroadcast(@Req() req: Request, @Body() body: any) { const session = this.auth.assert(req); return this.broadcasts.create(body, session.actor) }

  @Patch('broadcasts/:id')
  updateBroadcast(@Req() req: Request, @Param('id') id: string, @Body() body: any) { this.auth.assert(req); return this.broadcasts.update(id, body) }

  @Post('broadcasts/test')
  testBroadcast(@Req() req: Request, @Body() body: any) { this.auth.assert(req); return this.broadcasts.test(body) }

  @Post('broadcasts/:id/send')
  sendBroadcast(@Req() req: Request, @Param('id') id: string, @Body() body: any) { this.auth.assert(req); return this.broadcasts.processCampaign(id, Number(body?.max) || 300) }

  @Delete('broadcasts/:id')
  deleteBroadcast(@Req() req: Request, @Param('id') id: string) { this.auth.assert(req); return this.broadcasts.remove(id) }

  @Get('events')
  @Header('Cache-Control', 'private, no-store')
  list(@Req() req: Request) { this.auth.assert(req); return this.events.listAdmin() }

  @Post('events')
  create(@Req() req: Request, @Body() body: any) { this.auth.assert(req); return this.events.create(body) }

  @Patch('events/:id')
  update(@Req() req: Request, @Param('id') id: string, @Body() body: any) { this.auth.assert(req); return this.events.update(id, body) }

  @Delete('events/:id')
  remove(@Req() req: Request, @Param('id') id: string) { this.auth.assert(req); return this.events.remove(id) }
}
