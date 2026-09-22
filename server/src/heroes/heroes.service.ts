import { Injectable, NotFoundException } from '@nestjs/common'
import { InjectModel } from '@nestjs/mongoose'
import { Types } from 'mongoose'
import type { Model } from 'mongoose'
import { Hero, type HeroDocument } from './schemas/hero.schema.js'

function escapeRegex(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

const CARD_PROJECTION = {
  _id: 1,
  id: 1,
  name: 1,
  date: 1,
  first_name: 1,
  last_name: 1,
  birth_date: 1,
  death_date: 1,
  region: 1,
  war: 1,
  img_url: 1,
} as const

function text(value: unknown) {
  return typeof value === 'string' ? value.trim() : value == null ? '' : String(value).trim()
}

function normalizeHero(raw: any, includeDetails = false) {
  if (!raw) return null

  const objectId = raw._id != null ? String(raw._id) : ''
  const id = text(raw.id) || objectId
  const first = text(raw?.name?.first) || text(raw.first_name)
  const last = text(raw?.name?.last) || text(raw.last_name)
  const birth = text(raw?.date?.birth) || text(raw.birth_date)
  const dead = text(raw?.date?.dead) || text(raw.death_date)

  const normalized: Record<string, unknown> = {
    id,
    name: { first, last },
    date: { birth, dead },
    // Flat aliases keep the React UI and older clients backward-compatible.
    first_name: first,
    last_name: last,
    birth_date: birth,
    death_date: dead,
    region: text(raw.region),
    war: text(raw.war),
    img_url: text(raw.img_url),
  }

  if (includeDetails) {
    normalized.bio_link = text(raw.bio_link)
    normalized.bio = text(raw.bio)
    if (raw.created_at != null) normalized.created_at = raw.created_at
    if (raw.updated_at != null) normalized.updated_at = raw.updated_at
  }

  return normalized
}

@Injectable()
export class HeroesService {
  constructor(@InjectModel(Hero.name) private readonly heroes: Model<HeroDocument>) {}

  async list(params: { q?: string; war?: string; region?: string; page?: number; limit?: number }) {
    const page = Math.max(1, Number(params.page) || 1)
    const limit = Math.min(40, Math.max(1, Number(params.limit) || 18))
    const filter: Record<string, any> = {}

    const q = (params.q || '').trim().replace(/\s+/g, ' ')
    if (q) {
      const tokens = q.split(' ').filter(Boolean).slice(0, 6).map(escapeRegex)
      filter.$and = tokens.map((token) => ({
        $or: [
          { 'name.first': { $regex: token, $options: 'i' } },
          { 'name.last': { $regex: token, $options: 'i' } },
          // Legacy flat fields for records imported by an older version.
          { first_name: { $regex: token, $options: 'i' } },
          { last_name: { $regex: token, $options: 'i' } },
          { region: { $regex: token, $options: 'i' } },
          { war: { $regex: token, $options: 'i' } },
        ],
      }))
    }

    if (params.war) filter.war = params.war
    if (params.region) filter.region = params.region

    const [documents, total] = await Promise.all([
      this.heroes
        .find(filter, CARD_PROJECTION)
        .sort({ 'name.first': 1, 'name.last': 1, first_name: 1, last_name: 1, _id: 1 })
        .skip((page - 1) * limit)
        .limit(limit)
        .lean(),
      this.heroes.countDocuments(filter),
    ])

    return {
      items: documents.map((hero: any) => normalizeHero(hero)),
      pagination: {
        page,
        limit,
        total,
        pages: Math.max(1, Math.ceil(total / limit)),
        hasMore: page * limit < total,
      },
    }
  }

  async get(id: string) {
    const cleanId = String(id || '').trim()
    if (!cleanId) throw new NotFoundException('Hero not found')

    const choices: Record<string, unknown>[] = [{ id: cleanId }]
    if (Types.ObjectId.isValid(cleanId)) choices.unshift({ _id: new Types.ObjectId(cleanId) })

    const hero = await this.heroes.findOne({ $or: choices }).lean()
    if (!hero) throw new NotFoundException('Hero not found')
    return normalizeHero(hero, true)
  }

  async random(limit = 6) {
    const size = Math.min(12, Math.max(1, Number(limit) || 6))
    const documents = await this.heroes.aggregate([
      { $sample: { size } },
      { $project: CARD_PROJECTION },
    ])
    return documents.map((hero: any) => normalizeHero(hero))
  }

  async heroOfDay() {
    const total = await this.heroes.countDocuments({})
    if (!total) return null

    const dateKey = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Yerevan',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(new Date())

    let hash = 0
    for (const char of dateKey) hash = ((hash << 5) - hash + char.charCodeAt(0)) | 0
    const skip = Math.abs(hash) % total

    const hero = await this.heroes.findOne({}, CARD_PROJECTION).sort({ _id: 1 }).skip(skip).lean()
    return normalizeHero(hero)
  }

  async filters() {
    const [wars, regions] = await Promise.all([
      this.heroes.distinct('war', { war: { $nin: ['', null] } }),
      this.heroes.distinct('region', { region: { $nin: ['', null] } }),
    ])

    const cleanWars = (wars as unknown[]).map((value) => text(value)).filter(Boolean)
    const cleanRegions = (regions as unknown[]).map((value) => text(value)).filter(Boolean)

    return {
      wars: [...new Set(cleanWars)].sort((a: string, b: string) => a.localeCompare(b, 'hy')),
      regions: [...new Set(cleanRegions)].sort((a: string, b: string) => a.localeCompare(b, 'hy')),
    }
  }

  count() {
    return this.heroes.countDocuments({})
  }
}
