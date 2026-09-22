import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common'
import type { OnModuleInit } from '@nestjs/common'
import { InjectConnection } from '@nestjs/mongoose'
import { Types } from 'mongoose'
import type { Connection } from 'mongoose'

const nowIso = () => new Date().toISOString()
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
const clean = (value: unknown, max = 4000) => String(value ?? '').trim().slice(0, max)
const bool = (value: unknown) => Boolean(value)

function audienceFilter(campaign: any) {
  const filter: any = { moderation_status: { $nin: ['blocked', 'restricted'] } }
  if (campaign.language) filter.language_code = campaign.language
  const now = Date.now()
  if (campaign.audience === 'active24h') filter.last_seen_at = { $gte: new Date(now - 24 * 60 * 60 * 1000).toISOString() }
  if (campaign.audience === 'active7d') filter.last_seen_at = { $gte: new Date(now - 7 * 24 * 60 * 60 * 1000).toISOString() }
  if (campaign.audience === 'active30d') filter.last_seen_at = { $gte: new Date(now - 30 * 24 * 60 * 60 * 1000).toISOString() }
  return filter
}

type ButtonType = 'url' | 'web_app' | 'popup' | 'copy' | 'callback' | 'login_url' | 'switch_inline' | 'switch_inline_current' | 'switch_inline_chosen'

function sanitizeButtons(input: any) {
  const rows = Array.isArray(input) ? input : []
  const supported = new Set<ButtonType>(['url', 'web_app', 'popup', 'copy', 'callback', 'login_url', 'switch_inline', 'switch_inline_current', 'switch_inline_chosen'])
  return rows.slice(0, 20).map((raw: any, index: number) => {
    const type = supported.has(raw?.type) ? raw.type : 'url'
    const style = ['primary', 'success', 'danger'].includes(String(raw?.style)) ? String(raw.style) : ''
    const chosen = Array.isArray(raw?.chosen_chat_types) ? raw.chosen_chat_types.filter((x: any) => ['users', 'bots', 'groups', 'channels'].includes(String(x))).slice(0, 4) : []
    return {
      id: clean(raw?.id || `btn-${index + 1}`, 40),
      row: Math.min(9, Math.max(0, Number(raw?.row) || 0)),
      type,
      text: clean(raw?.text, 64),
      value: clean(raw?.value ?? raw?.url, 1500),
      popup_text: clean(raw?.popup_text, 180),
      style,
      icon_custom_emoji_id: clean(raw?.icon_custom_emoji_id, 80),
      chosen_chat_types: chosen,
    }
  }).filter((button: any) => button.text && (button.type === 'popup' ? button.popup_text : button.value || button.type === 'switch_inline' || button.type === 'switch_inline_current' || button.type === 'switch_inline_chosen'))
}

@Injectable()
export class BroadcastsService implements OnModuleInit {
  constructor(@InjectConnection() private readonly connection: Connection) {}

  private campaignsCollection() { return this.connection.collection('broadcasts') }
  private deliveriesCollection() { return this.connection.collection('broadcast_deliveries') }
  private usersCollection() { return this.connection.collection('users') }

  async onModuleInit() {
    try {
      await Promise.all([
        this.campaignsCollection().createIndex({ created_at: -1 }),
        this.deliveriesCollection().createIndex({ campaign_id: 1, user_id: 1 }, { unique: true }),
        this.deliveriesCollection().createIndex({ created_at: -1 }),
      ])
    } catch {}
  }

  private autoTitle(message: string) {
    const plain = message
      .replace(/<[^>]+>/g, ' ')
      .replace(/[*_~`>#\[\]()\\]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
    if (plain) return plain.slice(0, 72)
    return `Broadcast · ${new Date().toISOString().slice(0, 16).replace('T', ' ')}`
  }

  private sanitize(body: any) {
    const message = clean(body?.message, 3900)
    const title = clean(body?.title, 160) || this.autoTitle(message)
    const audience = ['all', 'active24h', 'active7d', 'active30d'].includes(String(body?.audience)) ? String(body.audience) : 'all'
    const parseMode = ['HTML', 'MarkdownV2', 'Markdown', 'none'].includes(String(body?.parse_mode)) ? String(body.parse_mode) : 'HTML'
    const mediaType = ['none', 'photo', 'video', 'animation', 'document'].includes(String(body?.media_type)) ? String(body.media_type) : 'none'
    const mediaUrl = clean(body?.media_url || body?.image_url, 1500)
    return {
      title,
      message,
      audience,
      language: clean(body?.language, 12),
      parse_mode: parseMode,
      media_type: mediaType,
      media_url: mediaUrl,
      buttons: sanitizeButtons(body?.buttons),
      silent: bool(body?.silent),
      protect_content: bool(body?.protect_content),
      link_preview: body?.link_preview !== false,
      message_effect_id: clean(body?.message_effect_id, 100),
    }
  }

  private assertSendable(campaign: any) {
    const hasMessage = Boolean(clean(campaign?.message, 3900))
    const mediaType = String(campaign?.media_type || 'none')
    const hasMedia = mediaType !== 'none' && Boolean(clean(campaign?.media_url, 1500))
    if (!hasMessage && !hasMedia) throw new BadRequestException('Add a message or media before sending')
    if (mediaType !== 'none' && !campaign?.media_url) throw new BadRequestException('Media URL is required for selected media type')

    for (const button of Array.isArray(campaign?.buttons) ? campaign.buttons : []) {
      const value = String(button?.value || '').trim()
      if (button.type === 'web_app' && !/^https:\/\//i.test(value)) throw new BadRequestException(`Web App button “${button.text}” requires an HTTPS URL`)
      if (button.type === 'login_url' && !/^https:\/\//i.test(value)) throw new BadRequestException(`Login URL button “${button.text}” requires an HTTPS URL`)
      if (button.type === 'url' && !/^(https?:\/\/|tg:\/\/)/i.test(value)) throw new BadRequestException(`Link button “${button.text}” requires an http(s) or tg:// URL`)
    }
  }

  async stats() {
    const [total, queued, sent, failed, deliveries30] = await Promise.all([
      this.campaignsCollection().countDocuments({}),
      this.campaignsCollection().countDocuments({ status: { $in: ['draft', 'queued', 'sending'] } }),
      this.campaignsCollection().countDocuments({ status: 'sent' }),
      this.campaignsCollection().countDocuments({ status: 'failed' }),
      this.deliveriesCollection().countDocuments({ status: 'sent', created_at: { $gte: new Date(Date.now() - 30 * 86400000).toISOString() } }),
    ])
    return { total, queued, sent, failed, deliveries30 }
  }

  async list(limit = 80) {
    const items = await this.campaignsCollection().find({}).sort({ created_at: -1 }).limit(Math.min(150, Math.max(10, Number(limit) || 80))).toArray()
    return items.map((item: any) => ({ ...item, id: String(item._id), _id: undefined }))
  }

  async deliveries(id: string, limit = 100) {
    if (!Types.ObjectId.isValid(id)) throw new NotFoundException('Broadcast not found')
    const items = await this.deliveriesCollection().find({ campaign_id: id }).sort({ created_at: -1 }).limit(Math.min(300, Math.max(10, Number(limit) || 100))).toArray()
    return items.map((item: any) => ({ ...item, id: String(item._id), _id: undefined }))
  }

  async create(body: any, actor = 'admin') {
    const payload = this.sanitize(body)
    const now = nowIso()
    const target_count = await this.usersCollection().countDocuments(audienceFilter(payload))
    const doc = { ...payload, status: 'draft', target_count, sent_count: 0, failed_count: 0, skipped_count: 0, created_at: now, updated_at: now, created_by: actor, started_at: '', completed_at: '', last_error: '' }
    const result = await this.campaignsCollection().insertOne(doc)
    return { ...doc, id: String(result.insertedId) }
  }

  async update(id: string, body: any) {
    if (!Types.ObjectId.isValid(id)) throw new NotFoundException('Broadcast not found')
    const current: any = await this.campaignsCollection().findOne({ _id: new Types.ObjectId(id) })
    if (!current) throw new NotFoundException('Broadcast not found')
    if (current.status === 'sending') throw new BadRequestException('Cannot edit while sending')
    const payload = this.sanitize({ ...current, ...body })
    const target_count = await this.usersCollection().countDocuments(audienceFilter(payload))
    await this.campaignsCollection().updateOne({ _id: new Types.ObjectId(id) }, { $set: { ...payload, target_count, updated_at: nowIso() } })
    return this.campaignsCollection().findOne({ _id: new Types.ObjectId(id) }).then((item: any) => ({ ...item, id: String(item._id), _id: undefined }))
  }

  async remove(id: string) {
    if (!Types.ObjectId.isValid(id)) throw new NotFoundException('Broadcast not found')
    const current: any = await this.campaignsCollection().findOne({ _id: new Types.ObjectId(id) })
    if (!current) throw new NotFoundException('Broadcast not found')
    if (current.status === 'sending') throw new BadRequestException('Cannot delete a broadcast while sending')
    await Promise.all([this.campaignsCollection().deleteOne({ _id: new Types.ObjectId(id) }), this.deliveriesCollection().deleteMany({ campaign_id: id })])
    return { ok: true }
  }

  private buildKeyboard(campaign: any, campaignId = 'test') {
    const grouped = new Map<number, any[]>()
    const buttons = Array.isArray(campaign.buttons) ? campaign.buttons : []
    buttons.forEach((button: any, index: number) => {
      const item: any = { text: button.text }
      if (button.style) item.style = button.style
      if (button.icon_custom_emoji_id) item.icon_custom_emoji_id = button.icon_custom_emoji_id
      if (button.type === 'url') item.url = button.value
      if (button.type === 'web_app') item.web_app = { url: button.value }
      if (button.type === 'login_url') item.login_url = { url: button.value }
      if (button.type === 'copy') item.copy_text = { text: button.value.slice(0, 256) }
      if (button.type === 'callback') item.callback_data = button.value.slice(0, 64)
      if (button.type === 'popup') item.callback_data = `hhpopup:${campaignId}:${index}`.slice(0, 64)
      if (button.type === 'switch_inline') item.switch_inline_query = button.value || ''
      if (button.type === 'switch_inline_current') item.switch_inline_query_current_chat = button.value || ''
      if (button.type === 'switch_inline_chosen') {
        const types = button.chosen_chat_types || []
        item.switch_inline_query_chosen_chat = {
          query: button.value || '',
          allow_user_chats: !types.length || types.includes('users'),
          allow_bot_chats: types.includes('bots'),
          allow_group_chats: types.includes('groups'),
          allow_channel_chats: types.includes('channels'),
        }
      }
      const row = Number(button.row) || 0
      if (!grouped.has(row)) grouped.set(row, [])
      grouped.get(row)!.push(item)
    })
    const inline_keyboard = [...grouped.entries()].sort(([a], [b]) => a - b).map(([, items]) => items.slice(0, 8)).filter((row) => row.length)
    return inline_keyboard.length ? { inline_keyboard } : undefined
  }

  private async telegramSend(userId: string, campaign: any, campaignId = 'test') {
    const token = process.env.BOT_TOKEN?.trim()
    if (!token) throw new Error('BOT_TOKEN is not configured')
    this.assertSendable(campaign)

    const call = async (method: string, payload: any) => {
      const response = await fetch(`https://api.telegram.org/bot${token}/${method}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) })
      const data: any = await response.json().catch(() => ({}))
      if (!response.ok || !data?.ok) {
        const retry = Number(data?.parameters?.retry_after || 0)
        if (retry > 0) await sleep(Math.min(10, retry) * 1000)
        throw new Error(clean(data?.description || `Telegram HTTP ${response.status}`, 500))
      }
      return data.result
    }

    const common: any = { chat_id: userId, disable_notification: Boolean(campaign.silent), protect_content: Boolean(campaign.protect_content) }
    if (campaign.message_effect_id) common.message_effect_id = campaign.message_effect_id
    const keyboard = this.buildKeyboard(campaign, campaignId)
    const parseMode = campaign.parse_mode && campaign.parse_mode !== 'none' ? campaign.parse_mode : undefined
    const message = String(campaign.message || '')
    const hasMedia = campaign.media_type && campaign.media_type !== 'none' && campaign.media_url

    if (hasMedia) {
      const methods: Record<string, [string, string]> = { photo: ['sendPhoto', 'photo'], video: ['sendVideo', 'video'], animation: ['sendAnimation', 'animation'], document: ['sendDocument', 'document'] }
      const spec = methods[campaign.media_type]
      if (!spec) throw new Error('Unsupported media type')

      // Telegram media captions are limited to 1024 characters. Keep media + text + buttons
      // in one native Telegram message when possible, otherwise send media then the long text.
      if (message && message.length <= 1000) {
        const payload: any = { ...common, [spec[1]]: campaign.media_url, caption: message }
        if (parseMode) payload.parse_mode = parseMode
        if (keyboard) payload.reply_markup = keyboard
        await call(spec[0], payload)
        return
      }

      await call(spec[0], { ...common, [spec[1]]: campaign.media_url })
      if (!message) return
    }

    const payload: any = {
      ...common,
      text: message,
      link_preview_options: { is_disabled: campaign.link_preview === false },
    }
    if (parseMode) payload.parse_mode = parseMode
    if (keyboard) payload.reply_markup = keyboard
    await call('sendMessage', payload)
  }

  async test(body: any) {
    const userId = clean(body?.user_id, 40)
    if (!/^\d+$/.test(userId)) throw new BadRequestException('Valid Telegram user ID is required')
    const campaign = this.sanitize(body)
    // Popup callback buttons in tests use a short-lived synthetic id; use campaign sends to fully test popup lookup.
    await this.telegramSend(userId, campaign, 'test')
    return { ok: true }
  }

  async processCampaign(id: string, max = 300) {
    if (!Types.ObjectId.isValid(id)) throw new NotFoundException('Broadcast not found')
    const objectId = new Types.ObjectId(id)
    const campaign: any = await this.campaignsCollection().findOne({ _id: objectId })
    if (!campaign) throw new NotFoundException('Broadcast not found')
    this.assertSendable(campaign)
    const batchLimit = Math.min(500, Math.max(1, Number(max) || 300))
    const filter = audienceFilter(campaign)
    const targetCount = await this.usersCollection().countDocuments(filter)
    const deliveredRows = await this.deliveriesCollection().find({ campaign_id: id, status: 'sent' }, { projection: { user_id: 1 } }).toArray()
    const doneIds = deliveredRows.map((row: any) => String(row.user_id)).filter(Boolean)
    const pendingFilter: any = { ...filter }
    if (doneIds.length) pendingFilter.id = { $nin: doneIds }
    const pending = await this.usersCollection().find(pendingFilter, { projection: { _id: 0, id: 1 } }).sort({ last_seen_at: -1 }).limit(batchLimit).toArray()

    const start = nowIso()
    await this.campaignsCollection().updateOne({ _id: objectId }, { $set: { status: pending.length ? 'sending' : 'sent', started_at: campaign.started_at || start, updated_at: start, target_count: targetCount } })
    let sent = 0, failed = 0
    for (const user of pending) {
      const userId = String(user.id)
      try {
        await this.telegramSend(userId, campaign, id)
        sent += 1
        await this.deliveriesCollection().updateOne(
          { campaign_id: id, user_id: userId },
          { $set: { status: 'sent', error: '', updated_at: nowIso() }, $setOnInsert: { campaign_id: id, user_id: userId, created_at: nowIso() }, $inc: { attempts: 1 } },
          { upsert: true },
        )
      } catch (error: any) {
        failed += 1
        await this.deliveriesCollection().updateOne(
          { campaign_id: id, user_id: userId },
          { $set: { status: 'failed', error: clean(error?.message, 500), updated_at: nowIso() }, $setOnInsert: { campaign_id: id, user_id: userId, created_at: nowIso() }, $inc: { attempts: 1 } },
          { upsert: true },
        )
      }
      await sleep(45)
    }

    const [sentCount, failedCount] = await Promise.all([
      this.deliveriesCollection().countDocuments({ campaign_id: id, status: 'sent' }),
      this.deliveriesCollection().countDocuments({ campaign_id: id, status: 'failed' }),
    ])
    const processed = sentCount + failedCount
    const completed = processed >= targetCount || pending.length === 0
    const status = completed ? (sentCount > 0 || targetCount === 0 ? 'sent' : 'failed') : 'queued'
    await this.campaignsCollection().updateOne({ _id: objectId }, { $set: { status, target_count: targetCount, sent_count: sentCount, failed_count: failedCount, updated_at: nowIso(), completed_at: completed ? nowIso() : '', last_error: failed ? `${failed} delivery failures in last batch` : '' } })
    return { ok: true, status, batch: pending.length, sent, failed, target: targetCount, sentTotal: sentCount, failedTotal: failedCount, remaining: Math.max(0, targetCount - processed) }
  }
}
