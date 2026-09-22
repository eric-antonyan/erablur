import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common'
import { InjectModel } from '@nestjs/mongoose'
import type { Model } from 'mongoose'
import type { TelegramMiniAppUser } from '../auth/telegram-auth.js'
import {
  AdminAudit,
  type AdminAuditDocument,
  SearchHistory,
  type SearchHistoryDocument,
  User,
  type ModerationStatus,
  type UserDocument,
} from './schemas/user.schema.js'

const nowIso = () => new Date().toISOString()

function cleanText(value: unknown, max = 500) {
  return String(value ?? '').trim().slice(0, max)
}

@Injectable()
export class UsersService {
  constructor(
    @InjectModel(User.name) private readonly users: Model<UserDocument>,
    @InjectModel(SearchHistory.name) private readonly history: Model<SearchHistoryDocument>,
    @InjectModel(AdminAudit.name) private readonly audit: Model<AdminAuditDocument>,
  ) {}

  private async normalizeRestriction(user: any) {
    if (!user) return user
    if (user.moderation_status === 'restricted' && user.restricted_until) {
      const until = Date.parse(user.restricted_until)
      if (Number.isFinite(until) && until <= Date.now()) {
        await this.users.updateOne({ id: user.id }, {
          $set: {
            moderation_status: 'active',
            moderation_reason: '',
            restricted_until: '',
            moderated_at: nowIso(),
          },
        })
        return { ...user, moderation_status: 'active', moderation_reason: '', restricted_until: '' }
      }
    }
    return user
  }

  moderationSnapshot(user: any) {
    const status: ModerationStatus = ['blocked', 'restricted'].includes(user?.moderation_status)
      ? user.moderation_status
      : 'active'
    return {
      status,
      reason: cleanText(user?.moderation_reason, 300),
      note: cleanText(user?.moderation_note, 500),
      restricted_until: cleanText(user?.restricted_until, 64),
      moderated_at: cleanText(user?.moderated_at, 64),
    }
  }

  async ensureUser(tg: TelegramMiniAppUser) {
    const now = nowIso()
    await this.users.updateOne(
      { id: String(tg.id) },
      {
        $set: {
          username: tg.username || '',
          first_name: tg.first_name || '',
          last_name: tg.last_name || '',
          language_code: tg.language_code || '',
          photo_url: tg.photo_url || '',
          last_seen_at: now,
          updated_at: now,
        },
        $setOnInsert: {
          id: String(tg.id),
          search_count: 0,
          joined_at: now,
          moderation_status: 'active',
        },
      },
      { upsert: true },
    )
    const user = await this.users.findOne({ id: String(tg.id) }, { _id: 0 }).lean()
    return this.normalizeRestriction(user)
  }

  async findByTelegramId(id: string) {
    const user = await this.users.findOne({ id: String(id) }, { _id: 0 }).lean()
    return this.normalizeRestriction(user)
  }

  async me(tg: TelegramMiniAppUser) {
    const user = await this.ensureUser(tg)
    const recent = await this.history
      .find({ user_id: String(tg.id) }, { _id: 0 })
      .sort({ searched_at: -1 })
      .limit(12)
      .lean()
    return { user, moderation: this.moderationSnapshot(user), recent }
  }

  async addHistory(tg: TelegramMiniAppUser, body: { query?: string; heroId?: string; heroName?: string }) {
    await this.ensureUser(tg)
    const query = cleanText(body.query || body.heroName, 200)
    if (!query) return { ok: true }
    const now = nowIso()
    await Promise.all([
      this.history.create({
        user_id: String(tg.id),
        query,
        hero_id: cleanText(body.heroId, 120),
        hero_name: cleanText(body.heroName, 160),
        searched_at: now,
      }),
      this.users.updateOne(
        { id: String(tg.id) },
        { $inc: { search_count: 1 }, $set: { last_query: query, last_seen_at: now, updated_at: now } },
      ),
    ])
    return { ok: true }
  }

  async clearHistory(tg: TelegramMiniAppUser) {
    const result = await this.history.deleteMany({ user_id: String(tg.id) })
    return { ok: true, deleted: result.deletedCount }
  }

  async adminList(params: { q?: string; status?: string; page?: number; limit?: number }) {
    const page = Math.max(1, Number(params.page) || 1)
    const limit = Math.min(100, Math.max(10, Number(params.limit) || 30))
    const filter: any = {}
    const q = cleanText(params.q, 120)
    const status = cleanText(params.status, 30)
    if (['active', 'restricted', 'blocked'].includes(status)) filter.moderation_status = status
    if (q) {
      const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      const rx = new RegExp(escaped, 'i')
      filter.$or = [{ id: rx }, { username: rx }, { first_name: rx }, { last_name: rx }]
    }

    const [items, total] = await Promise.all([
      this.users.find(filter, { _id: 0 }).sort({ last_seen_at: -1, joined_at: -1 }).skip((page - 1) * limit).limit(limit).lean(),
      this.users.countDocuments(filter),
    ])
    return { items, total, page, pages: Math.max(1, Math.ceil(total / limit)), limit }
  }

  async adminStats() {
    const since24h = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
    const [total, blocked, restricted, active24h, searches] = await Promise.all([
      this.users.countDocuments({}),
      this.users.countDocuments({ moderation_status: 'blocked' }),
      this.users.countDocuments({ moderation_status: 'restricted' }),
      this.users.countDocuments({ last_seen_at: { $gte: since24h } }),
      this.users.aggregate([{ $group: { _id: null, total: { $sum: '$search_count' } } }]),
    ])
    return { total, blocked, restricted, active24h, searches: Number(searches?.[0]?.total || 0) }
  }

  async adminGet(id: string) {
    const user = await this.findByTelegramId(id)
    if (!user) throw new NotFoundException('User not found')
    const [recent, audit] = await Promise.all([
      this.history.find({ user_id: String(id) }, { _id: 0 }).sort({ searched_at: -1 }).limit(30).lean(),
      this.audit.find({ user_id: String(id) }, { _id: 0 }).sort({ created_at: -1 }).limit(20).lean(),
    ])
    return { user, moderation: this.moderationSnapshot(user), recent, audit }
  }

  async moderate(id: string, body: any, actor = 'admin') {
    const action = cleanText(body?.action, 30)
    if (!['block', 'restrict', 'restore', 'unblock'].includes(action)) throw new BadRequestException('Invalid moderation action')
    const current = await this.users.findOne({ id: String(id) }, { _id: 0 }).lean()
    if (!current) throw new NotFoundException('User not found')

    let status: ModerationStatus = 'active'
    let restrictedUntil = ''
    if (action === 'block') status = 'blocked'
    if (action === 'restrict') {
      status = 'restricted'
      const explicit = cleanText(body?.restricted_until, 64)
      const durationMinutes = Math.min(365 * 24 * 60, Math.max(1, Number(body?.duration_minutes) || 60))
      restrictedUntil = explicit && Number.isFinite(Date.parse(explicit))
        ? new Date(explicit).toISOString()
        : new Date(Date.now() + durationMinutes * 60_000).toISOString()
    }

    const now = nowIso()
    const reason = cleanText(body?.reason, 300)
    const note = cleanText(body?.note, 1000)
    await Promise.all([
      this.users.updateOne({ id: String(id) }, {
        $set: {
          moderation_status: status,
          moderation_reason: status === 'active' ? '' : reason,
          moderation_note: note,
          restricted_until: restrictedUntil,
          moderated_at: now,
          moderated_by: actor,
          updated_at: now,
        },
      }),
      this.audit.create({ action, user_id: String(id), reason, note, restricted_until: restrictedUntil, created_at: now, actor }),
    ])
    return this.adminGet(id)
  }

  async clearHistoryAdmin(id: string) {
    const result = await this.history.deleteMany({ user_id: String(id) })
    return { ok: true, deleted: result.deletedCount }
  }
}
