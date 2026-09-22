import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common'
import { InjectModel } from '@nestjs/mongoose'
import { Types } from 'mongoose'
import type { Model } from 'mongoose'
import { EventsService } from '../events/events.service.js'
import { UsersService } from '../users/users.service.js'
import { EventReminder, type EventReminderDocument, ReminderDelivery, type ReminderDeliveryDocument } from './schemas/reminder.schema.js'

const ALLOWED_OFFSETS = new Set([0, 1, 3, 7, 14, 30])

function nowIso() { return new Date().toISOString() }

function yerevanDate(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Yerevan', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(date)
  const value = (type: string) => parts.find((part) => part.type === type)?.value || ''
  return `${value('year')}-${value('month')}-${value('day')}`
}

function validDate(value: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(`${value}T00:00:00Z`))
}

function shiftDate(value: string, days: number) {
  const date = new Date(`${value}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

function annualOccurrenceAfter(sourceDate: string, afterDate: string) {
  if (!validDate(sourceDate) || !validDate(afterDate)) return sourceDate
  const [, month, day] = sourceDate.split('-').map(Number)
  let year = Number(afterDate.slice(0, 4))
  const build = (y: number) => {
    const last = new Date(Date.UTC(y, month, 0)).getUTCDate()
    const safeDay = Math.min(day, last)
    return `${y}-${String(month).padStart(2, '0')}-${String(safeDay).padStart(2, '0')}`
  }
  let value = build(year)
  if (value < afterDate) value = build(year + 1)
  return value
}

function scheduleFor(event: any, offsetDays: number, today = yerevanDate()) {
  let occurrence = String(event?.next_date || event?.date || '')
  if (!validDate(occurrence)) return null
  if (event?.annual !== false) occurrence = annualOccurrenceAfter(String(event.date || occurrence), today)
  if (event?.annual === false && occurrence < today) return null
  let sendDate = shiftDate(occurrence, -offsetDays)
  // If a user enables a reminder after the preferred reminder date, send on the next task run.
  if (sendDate < today && occurrence >= today) sendDate = today
  return { occurrence, sendDate }
}

function normalize(raw: any) {
  if (!raw) return null
  return {
    id: String(raw._id),
    user_id: String(raw.user_id || ''),
    event_id: String(raw.event_id || ''),
    event_title: String(raw.event_title || ''),
    offset_days: Number(raw.offset_days || 0),
    enabled: raw.enabled !== false,
    status: String(raw.status || 'active'),
    next_occurrence: String(raw.next_occurrence || ''),
    next_send_date: String(raw.next_send_date || ''),
    last_sent_occurrence: String(raw.last_sent_occurrence || ''),
    sent_count: Number(raw.sent_count || 0),
    last_sent_at: String(raw.last_sent_at || ''),
    last_error: String(raw.last_error || ''),
    attempts: Number(raw.attempts || 0),
    created_at: String(raw.created_at || ''),
    updated_at: String(raw.updated_at || ''),
  }
}

@Injectable()
export class RemindersService {
  constructor(
    @InjectModel(EventReminder.name) private readonly reminders: Model<EventReminderDocument>,
    @InjectModel(ReminderDelivery.name) private readonly deliveries: Model<ReminderDeliveryDocument>,
    private readonly events: EventsService,
    private readonly users: UsersService,
  ) {}

  private parseOffset(value: unknown) {
    const offset = Number(value)
    if (!ALLOWED_OFFSETS.has(offset)) throw new BadRequestException('offset_days must be one of 0, 1, 3, 7, 14, 30')
    return offset
  }

  async listForUser(userId: string) {
    const items = await this.reminders.find({ user_id: String(userId), enabled: true }).sort({ next_send_date: 1, event_title: 1 }).lean()
    return { items: items.map(normalize).filter(Boolean) }
  }

  async getForEvent(userId: string, eventId: string) {
    const reminder = await this.reminders.findOne({ user_id: String(userId), event_id: String(eventId), enabled: true }).lean()
    return { reminder: normalize(reminder) }
  }

  async upsert(tgUser: any, eventId: string, body: any) {
    const ensured = await this.users.ensureUser(tgUser)
    const userId = String(tgUser?.id || ensured?.id || '')
    if (!userId) throw new BadRequestException('Telegram user is required')
    const event: any = await this.events.getPublic(eventId)
    if (!event) throw new NotFoundException('Event not found')
    const offsetDays = this.parseOffset(body?.offset_days ?? 1)
    const schedule = scheduleFor(event, offsetDays)
    if (!schedule) throw new BadRequestException('This event can no longer be reminded')
    const now = nowIso()
    const result = await this.reminders.findOneAndUpdate(
      { user_id: String(userId), event_id: String(eventId) },
      {
        $set: {
          event_title: event.title,
          offset_days: offsetDays,
          enabled: true,
          status: 'active',
          next_occurrence: schedule.occurrence,
          next_send_date: schedule.sendDate,
          last_error: '',
          attempts: 0,
          processing_until: null,
          updated_at: now,
        },
        $setOnInsert: { created_at: now, sent_count: 0, last_sent_at: '', last_sent_occurrence: '' },
      },
      { upsert: true, new: true, setDefaultsOnInsert: true },
    ).lean()
    return { reminder: normalize(result) }
  }

  async cancel(userId: string, eventId: string) {
    const now = nowIso()
    await this.reminders.updateOne(
      { user_id: String(userId), event_id: String(eventId) },
      { $set: { enabled: false, status: 'cancelled', processing_until: null, updated_at: now } },
    )
    return { ok: true }
  }

  private async telegramSend(userId: string, event: any, occurrence: string) {
    const token = process.env.BOT_TOKEN?.trim()
    if (!token) throw new Error('BOT_TOKEN is not configured')
    const webapp = process.env.WEBAPP_URL?.trim().replace(/\/$/, '')
    const dateText = new Intl.DateTimeFormat('hy-AM', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Asia/Yerevan' })
      .format(new Date(`${occurrence}T12:00:00+04:00`))
    const text = `🔔 <b>Իրադարձության հիշեցում</b>\n\n<b>${String(event.title || 'Հիշարժան օր')}</b>\n📅 ${dateText}\n\nԲացիր «Հայոց Հերոսներ» Mini App-ը՝ մանրամասները դիտելու համար։`
    const payload: any = {
      chat_id: userId,
      text,
      parse_mode: 'HTML',
      disable_web_page_preview: true,
    }
    if (webapp) {
      payload.reply_markup = {
        inline_keyboard: [[{ text: 'Բացել իրադարձությունը', web_app: { url: `${webapp}/event/${event.id}` } }]],
      }
    }
    const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data: any = await response.json().catch(() => null)
    if (!response.ok || !data?.ok) throw new Error(data?.description || `Telegram HTTP ${response.status}`)
    return data
  }

  async processDue(limit = 100) {
    const today = yerevanDate()
    const max = Math.min(300, Math.max(1, Number(limit) || 100))
    const started = nowIso()
    const results = { processed: 0, sent: 0, failed: 0, suppressed: 0, cancelled: 0, started_at: started, today }

    // Refresh active reminder schedules so event-date changes made by admin are picked up automatically.
    const active = await this.reminders.find({ enabled: true, status: 'active' }).limit(1500).lean()
    for (const raw of active) {
      try {
        const event: any = await this.events.getPublic(String(raw.event_id))
        if (!event) throw new Error('Event unavailable')
        const schedule = scheduleFor(event, Number(raw.offset_days || 0), today)
        if (!schedule) {
          await this.reminders.updateOne({ _id: raw._id }, { $set: { enabled: false, status: 'cancelled', last_error: 'Event has expired', updated_at: nowIso() } })
          continue
        }
        if (raw.next_occurrence !== schedule.occurrence || raw.next_send_date !== schedule.sendDate || raw.event_title !== event.title) {
          await this.reminders.updateOne({ _id: raw._id }, { $set: { event_title: event.title, next_occurrence: schedule.occurrence, next_send_date: schedule.sendDate, updated_at: nowIso() } })
        }
      } catch {
        await this.reminders.updateOne({ _id: raw._id }, { $set: { enabled: false, status: 'cancelled', last_error: 'Event unavailable', updated_at: nowIso() } })
      }
    }

    for (let index = 0; index < max; index += 1) {
      const now = new Date()
      const lockUntil = new Date(now.getTime() + 5 * 60_000)
      const reminder = await this.reminders.findOneAndUpdate(
        {
          enabled: true,
          status: 'active',
          next_send_date: { $lte: today },
          $or: [{ processing_until: null }, { processing_until: { $exists: false } }, { processing_until: { $lt: now } }],
        },
        { $set: { processing_until: lockUntil, last_attempt_at: now.toISOString(), updated_at: now.toISOString() }, $inc: { attempts: 1 } },
        { sort: { next_send_date: 1, created_at: 1 }, new: true },
      ).lean()
      if (!reminder) break
      results.processed += 1
      const reminderId = String(reminder._id)
      const userId = String(reminder.user_id)
      const eventId = String(reminder.event_id)
      const occurrence = String(reminder.next_occurrence || '')

      try {
        const user = await this.users.findByTelegramId(userId)
        const moderation = this.users.moderationSnapshot(user)
        if (!user || moderation.status !== 'active') {
          results.suppressed += 1
          const tomorrow = shiftDate(today, 1)
          await this.reminders.updateOne({ _id: reminder._id }, { $set: { processing_until: null, next_send_date: tomorrow, last_error: `Suppressed: ${moderation.status || 'user unavailable'}`, updated_at: nowIso() } })
          await this.deliveries.create({ reminder_id: reminderId, user_id: userId, event_id: eventId, event_title: reminder.event_title || '', occurrence, status: 'suppressed', error: moderation.status || 'user unavailable', created_at: nowIso() })
          continue
        }

        const event: any = await this.events.getPublic(eventId)
        if (!event) throw new Error('Event unavailable')
        if (reminder.last_sent_occurrence && reminder.last_sent_occurrence === occurrence) {
          if (event.annual !== false) {
            const nextOccurrence = annualOccurrenceAfter(String(event.date), shiftDate(occurrence, 1))
            await this.reminders.updateOne({ _id: reminder._id }, { $set: { next_occurrence: nextOccurrence, next_send_date: shiftDate(nextOccurrence, -Number(reminder.offset_days || 0)), processing_until: null, updated_at: nowIso() } })
          } else {
            await this.reminders.updateOne({ _id: reminder._id }, { $set: { enabled: false, status: 'sent', processing_until: null, updated_at: nowIso() } })
          }
          continue
        }

        await this.telegramSend(userId, event, occurrence)
        results.sent += 1
        const sentAt = nowIso()
        const update: any = {
          last_sent_occurrence: occurrence,
          last_sent_at: sentAt,
          last_error: '',
          attempts: 0,
          processing_until: null,
          updated_at: sentAt,
        }
        if (event.annual !== false) {
          const nextOccurrence = annualOccurrenceAfter(String(event.date), shiftDate(occurrence, 1))
          update.next_occurrence = nextOccurrence
          update.next_send_date = shiftDate(nextOccurrence, -Number(reminder.offset_days || 0))
          update.status = 'active'
          update.enabled = true
        } else {
          update.enabled = false
          update.status = 'sent'
          update.next_send_date = ''
        }
        await Promise.all([
          this.reminders.updateOne({ _id: reminder._id }, { $set: update, $inc: { sent_count: 1 } }),
          this.deliveries.create({ reminder_id: reminderId, user_id: userId, event_id: eventId, event_title: event.title || '', occurrence, status: 'sent', error: '', created_at: sentAt }),
        ])
      } catch (error: any) {
        results.failed += 1
        const attempts = Number(reminder.attempts || 1)
        const permanent = attempts >= 5
        await this.reminders.updateOne({ _id: reminder._id }, { $set: {
          processing_until: null,
          status: permanent ? 'failed' : 'active',
          enabled: !permanent,
          next_send_date: permanent ? String(reminder.next_send_date || today) : shiftDate(today, 1),
          last_error: String(error?.message || 'Delivery failed').slice(0, 1000),
          updated_at: nowIso(),
        } })
        await this.deliveries.create({ reminder_id: reminderId, user_id: userId, event_id: eventId, event_title: reminder.event_title || '', occurrence, status: 'failed', error: String(error?.message || 'Delivery failed').slice(0, 1000), created_at: nowIso() })
      }
    }

    return { ...results, finished_at: nowIso() }
  }

  async adminStats() {
    const today = yerevanDate()
    const monthAgo = new Date(Date.now() - 30 * 24 * 60 * 60_000).toISOString()
    const [active, due, failed, sent30] = await Promise.all([
      this.reminders.countDocuments({ enabled: true, status: 'active' }),
      this.reminders.countDocuments({ enabled: true, status: 'active', next_send_date: { $lte: today } }),
      this.reminders.countDocuments({ status: 'failed' }),
      this.deliveries.countDocuments({ status: 'sent', created_at: { $gte: monthAgo } }),
    ])
    return { active, due, failed, sent30, task_time: '09:00 Asia/Yerevan', today }
  }

  async adminList(params: { status?: string; limit?: number } = {}) {
    const filter: any = {}
    const status = String(params.status || '').trim()
    if (status) filter.status = status
    const limit = Math.min(300, Math.max(10, Number(params.limit) || 100))
    const items = await this.reminders.find(filter).sort({ next_send_date: 1, updated_at: -1 }).limit(limit).lean()
    return { items: items.map(normalize).filter(Boolean) }
  }

  async adminDeliveries(limit = 80) {
    const safe = Math.min(200, Math.max(10, Number(limit) || 80))
    const items = await this.deliveries.find({}, { _id: 0 }).sort({ created_at: -1 }).limit(safe).lean()
    return { items }
  }

  async adminCancel(id: string) {
    if (!Types.ObjectId.isValid(id)) throw new NotFoundException('Reminder not found')
    const result = await this.reminders.updateOne({ _id: id }, { $set: { enabled: false, status: 'cancelled', processing_until: null, updated_at: nowIso() } })
    if (!result.matchedCount) throw new NotFoundException('Reminder not found')
    return { ok: true }
  }
}
