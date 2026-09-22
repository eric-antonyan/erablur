import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common'
import { InjectConnection } from '@nestjs/mongoose'
import type { Connection } from 'mongoose'

export type AdminRole = 'owner' | 'admin'

const nowIso = () => new Date().toISOString()
const clean = (value: unknown, max = 300) => String(value ?? '').trim().slice(0, max)

@Injectable()
export class AdminsService {
  constructor(@InjectConnection() private readonly connection: Connection) {}

  ownerId() {
    return process.env.OWNER_TELEGRAM_ID?.trim() || '8182558373'
  }

  private collection() { return this.connection.collection('admins') }

  async ensureIndexes() {
    try {
      await Promise.all([
        this.collection().createIndex({ telegram_id: 1 }, { unique: true }),
        this.collection().createIndex({ active: 1, created_at: -1 }),
      ])
    } catch {}
  }

  async resolve(telegramId: string) {
    const id = clean(telegramId, 40)
    if (!/^\d+$/.test(id)) return null
    if (id === this.ownerId()) return { telegram_id: id, role: 'owner' as const, active: true, name: 'Owner', note: '', permissions: ['*'] }
    const admin: any = await this.collection().findOne({ telegram_id: id, active: { $ne: false } })
    if (!admin) return null
    return {
      telegram_id: id,
      role: 'admin' as const,
      active: true,
      name: clean(admin.name, 120),
      note: clean(admin.note, 400),
      permissions: Array.isArray(admin.permissions) ? admin.permissions.map((item: any) => clean(item, 80)).filter(Boolean) : ['users', 'events', 'reminders', 'broadcasts'],
    }
  }

  async list() {
    await this.ensureIndexes()
    const items: any[] = await this.collection().find({}).sort({ created_at: -1 }).toArray()
    return {
      owner: { telegram_id: this.ownerId(), role: 'owner', active: true, name: 'Owner', permissions: ['*'] },
      admins: items.map((item) => ({
        id: String(item._id), telegram_id: String(item.telegram_id || ''), role: 'admin', active: item.active !== false,
        name: clean(item.name, 120), note: clean(item.note, 400), permissions: item.permissions || [],
        created_at: item.created_at || '', created_by: item.created_by || '', updated_at: item.updated_at || '',
      })),
    }
  }

  async add(body: any, actor: string) {
    await this.ensureIndexes()
    const telegramId = clean(body?.telegram_id, 40)
    if (!/^\d+$/.test(telegramId)) throw new BadRequestException('Valid Telegram user ID is required')
    if (telegramId === this.ownerId()) throw new BadRequestException('Owner is already configured')
    const name = clean(body?.name, 120)
    const note = clean(body?.note, 400)
    const allowed = new Set(['users', 'events', 'reminders', 'broadcasts'])
    const permissions = Array.isArray(body?.permissions)
      ? [...new Set(body.permissions.map((item: any) => clean(item, 80)).filter((item: string) => allowed.has(item)))]
      : ['users', 'events', 'reminders', 'broadcasts']
    if (!permissions.length) throw new BadRequestException('Select at least one permission')
    const now = nowIso()
    await this.collection().updateOne({ telegram_id: telegramId }, {
      $set: { telegram_id: telegramId, active: true, name, note, permissions, updated_at: now },
      $setOnInsert: { created_at: now, created_by: actor },
    }, { upsert: true })
    return this.resolve(telegramId)
  }

  async remove(telegramId: string) {
    const id = clean(telegramId, 40)
    if (id === this.ownerId()) throw new BadRequestException('Owner cannot be removed')
    const result = await this.collection().deleteOne({ telegram_id: id })
    if (!result.deletedCount) throw new NotFoundException('Admin not found')
    return { ok: true }
  }
}
