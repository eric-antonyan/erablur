import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common'
import { InjectModel } from '@nestjs/mongoose'
import { Types } from 'mongoose'
import type { Model } from 'mongoose'
import { MemorialEvent, type MemorialEventDocument } from './schemas/event.schema.js'

function text(value: unknown, max = 4000) {
  return String(value ?? '').trim().slice(0, max)
}

function yerevanTodayParts() {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Yerevan', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date())
  const get = (type: string) => parts.find((p) => p.type === type)?.value || ''
  return { year: Number(get('year')), month: get('month'), day: get('day') }
}

function validDate(value: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(`${value}T00:00:00Z`))
}

function nextOccurrence(date: string, annual: boolean) {
  if (!validDate(date)) return date
  if (!annual) return date
  const [, month, day] = date.split('-')
  const today = yerevanTodayParts()
  const md = `${month}-${day}`
  const todayMd = `${today.month}-${today.day}`
  const year = md >= todayMd ? today.year : today.year + 1
  return `${year}-${month}-${day}`
}

function normalize(raw: any) {
  if (!raw) return null
  const date = text(raw.date, 10)
  const annual = raw.annual !== false
  return {
    id: String(raw._id),
    title: text(raw.title, 240),
    date,
    next_date: nextOccurrence(date, annual),
    annual,
    category: text(raw.category, 80) || 'history',
    description: text(raw.description, 12000),
    image_url: text(raw.image_url, 1500),
    hero_id: text(raw.hero_id, 120),
    source_url: text(raw.source_url, 1500),
    published: raw.published !== false,
    createdAt: raw.createdAt || null,
    updatedAt: raw.updatedAt || null,
  }
}

@Injectable()
export class EventsService {
  constructor(@InjectModel(MemorialEvent.name) private readonly events: Model<MemorialEventDocument>) {}

  async listPublic(params: { from?: string; to?: string; limit?: number } = {}) {
    const limit = Math.min(500, Math.max(1, Number(params.limit) || 100))
    const documents = await this.events.find({ published: true }).lean()
    let items = documents.map(normalize).filter(Boolean) as any[]
    if (params.from) items = items.filter((item) => item.next_date >= params.from!)
    if (params.to) items = items.filter((item) => item.next_date <= params.to!)
    items.sort((a, b) => a.next_date.localeCompare(b.next_date) || a.title.localeCompare(b.title, 'hy'))
    return { items: items.slice(0, limit), total: items.length }
  }

  async upcoming(limit = 8) {
    const today = yerevanTodayParts()
    const todayIso = `${today.year}-${today.month}-${today.day}`
    const { items } = await this.listPublic({ limit: 500 })
    return items.filter((item: any) => item.next_date >= todayIso).slice(0, Math.min(30, Math.max(1, limit || 8)))
  }

  async getPublic(id: string) {
    if (!Types.ObjectId.isValid(id)) throw new NotFoundException('Event not found')
    const event = await this.events.findOne({ _id: id, published: true }).lean()
    if (!event) throw new NotFoundException('Event not found')
    return normalize(event)
  }

  async listAdmin() {
    const docs = await this.events.find({}).sort({ date: 1, title: 1 }).lean()
    return docs.map(normalize)
  }

  private sanitize(body: any, partial = false) {
    const payload: Record<string, unknown> = {}
    if (!partial || body.title !== undefined) payload.title = text(body.title, 240)
    if (!partial || body.date !== undefined) {
      const date = text(body.date, 10)
      if (!validDate(date)) throw new BadRequestException('date must be YYYY-MM-DD')
      payload.date = date
    }
    if (!partial || body.annual !== undefined) payload.annual = Boolean(body.annual)
    if (!partial || body.category !== undefined) payload.category = text(body.category, 80) || 'history'
    if (!partial || body.description !== undefined) payload.description = text(body.description, 12000)
    if (!partial || body.image_url !== undefined) payload.image_url = text(body.image_url, 1500)
    if (!partial || body.hero_id !== undefined) payload.hero_id = text(body.hero_id, 120)
    if (!partial || body.source_url !== undefined) payload.source_url = text(body.source_url, 1500)
    if (!partial || body.published !== undefined) payload.published = body.published !== false
    if (!partial && !payload.title) throw new BadRequestException('title is required')
    return payload
  }

  async create(body: any) {
    const event = await this.events.create(this.sanitize(body))
    return normalize(event.toObject())
  }

  async update(id: string, body: any) {
    if (!Types.ObjectId.isValid(id)) throw new NotFoundException('Event not found')
    const event = await this.events.findByIdAndUpdate(id, { $set: this.sanitize(body, true) }, { new: true }).lean()
    if (!event) throw new NotFoundException('Event not found')
    return normalize(event)
  }

  async remove(id: string) {
    if (!Types.ObjectId.isValid(id)) throw new NotFoundException('Event not found')
    const result = await this.events.deleteOne({ _id: id })
    if (!result.deletedCount) throw new NotFoundException('Event not found')
    return { ok: true }
  }
}
