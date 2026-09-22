import 'reflect-metadata'
import { createServer as createHttpServer } from 'node:http'
import mongoose from 'mongoose'
import { WebSocket, WebSocketServer } from 'ws'
import { verifyAdminRealtimeToken } from '../server/src/admin/realtime-token.js'
import { verifyInitData } from '../server/src/auth/telegram-auth.js'
import { createServer as createNestServer } from '../server/src/bootstrap.js'

let nestPromise: ReturnType<typeof createNestServer> | undefined
let realtimeConnectionPromise: Promise<any> | null = null

function restoreApiPath(req: any) {
  const parsed = new URL(req.url || '/', 'http://localhost')
  const rawPath = parsed.searchParams.get('__path')
  if (!rawPath) return
  parsed.searchParams.delete('__path')
  const query = parsed.searchParams.toString()
  req.url = `/api/${rawPath}${query ? `?${query}` : ''}`
}

function isRealtimeRequest(req: any) {
  const parsed = new URL(req.url || '/', 'http://localhost')
  return parsed.pathname === '/api/realtime' || parsed.searchParams.get('__path') === 'realtime'
}

async function realtimeDb() {
  if (!realtimeConnectionPromise) {
    const uri = process.env.MONGODB_URL?.trim()
    if (!uri) throw new Error('MONGODB_URL is required')
    const connection = mongoose.createConnection(uri, {
      dbName: process.env.MONGODB_DB_NAME?.trim() || 'erablur',
      serverSelectionTimeoutMS: 7000,
      maxPoolSize: 4,
      minPoolSize: 0,
    })
    realtimeConnectionPromise = connection.asPromise()
  }
  return realtimeConnectionPromise
}

function send(ws: WebSocket, payload: any) {
  if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload))
}

function moderationSnapshot(user: any) {
  const raw = String(user?.moderation_status || 'active')
  let status = raw === 'blocked' || raw === 'restricted' ? raw : 'active'
  const restrictedUntil = String(user?.restricted_until || '')
  if (status === 'restricted' && restrictedUntil && Date.parse(restrictedUntil) <= Date.now()) status = 'active'
  return {
    status,
    reason: String(user?.moderation_reason || ''),
    note: String(user?.moderation_note || ''),
    restricted_until: status === 'restricted' ? restrictedUntil : '',
    moderated_at: String(user?.moderated_at || ''),
  }
}

function publicUser(user: any) {
  if (!user) return null
  const { _id, ...clean } = user
  return { ...clean, moderation: moderationSnapshot(user) }
}

async function applyModeration(collection: any, audit: any, userId: string, payload: any) {
  const action = String(payload?.action || '')
  if (!['block', 'restrict', 'restore', 'unblock'].includes(action)) throw new Error('Invalid moderation action')
  const exists = await collection.findOne({ id: String(userId) })
  if (!exists) throw new Error('User not found')
  const now = new Date().toISOString()
  const reason = String(payload?.reason || '').trim().slice(0, 300)
  const note = String(payload?.note || '').trim().slice(0, 1000)
  let status = 'active'
  let restrictedUntil = ''
  if (action === 'block') status = 'blocked'
  if (action === 'restrict') {
    status = 'restricted'
    const explicit = String(payload?.restricted_until || '').trim()
    const minutes = Math.min(525600, Math.max(1, Number(payload?.duration_minutes) || 60))
    restrictedUntil = explicit && Number.isFinite(Date.parse(explicit))
      ? new Date(explicit).toISOString()
      : new Date(Date.now() + minutes * 60_000).toISOString()
  }
  await Promise.all([
    collection.updateOne({ id: String(userId) }, { $set: {
      moderation_status: status,
      moderation_reason: status === 'active' ? '' : reason,
      moderation_note: note,
      restricted_until: restrictedUntil,
      moderated_at: now,
      moderated_by: 'admin-realtime',
      updated_at: now,
    } }),
    audit.insertOne({ action, user_id: String(userId), reason, note, restricted_until: restrictedUntil, created_at: now, actor: 'admin-realtime' }),
  ])
  return collection.findOne({ id: String(userId) })
}

const wss = new WebSocketServer({ noServer: true })

wss.on('connection', (ws) => {
  let authenticated = false
  let role: 'user' | 'admin' | '' = ''
  let userId = ''
  const changeStreams: any[] = []
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let authTimer: ReturnType<typeof setTimeout> | null = setTimeout(() => {
    if (!authenticated) ws.close(4401, 'Authentication required')
  }, 10_000)

  const cleanup = () => {
    if (authTimer) clearTimeout(authTimer)
    if (pollTimer) clearInterval(pollTimer)
    for (const stream of changeStreams) { try { stream?.close?.() } catch {} }
  }

  const watchUser = async (users: any, id: string) => {
    const push = async () => {
      const user = await users.findOne({ id })
      if (!user) return
      send(ws, { type: 'moderation:update', user: publicUser(user), moderation: moderationSnapshot(user) })
    }
    await push()
    try {
      const userStream = users.watch(
        [{ $match: { 'fullDocument.id': id, operationType: { $in: ['insert', 'update', 'replace'] } } }],
        { fullDocument: 'updateLookup' },
      )
      changeStreams.push(userStream)
      userStream.on('change', (change: any) => {
        if (change?.fullDocument) send(ws, { type: 'moderation:update', user: publicUser(change.fullDocument), moderation: moderationSnapshot(change.fullDocument) })
      })
      userStream.on('error', () => {
        try { userStream?.close?.() } catch {}
        if (!pollTimer) pollTimer = setInterval(push, 5000)
      })
    } catch {
      pollTimer = setInterval(push, 5000)
    }
  }


  const watchEvents = async (events: any) => {
    try {
      const eventStream = events.watch(
        [{ $match: { operationType: { $in: ['insert', 'update', 'replace', 'delete'] } } }],
        { fullDocument: 'updateLookup' },
      )
      changeStreams.push(eventStream)
      eventStream.on('change', (change: any) => {
        send(ws, { type: 'events:changed', operation: String(change?.operationType || 'update'), at: Date.now() })
      })
    } catch {}
  }

  const watchAdmin = async (users: any) => {
    try {
      const adminStream = users.watch(
        [{ $match: { operationType: { $in: ['insert', 'update', 'replace'] } } }],
        { fullDocument: 'updateLookup' },
      )
      changeStreams.push(adminStream)
      adminStream.on('change', (change: any) => {
        if (change?.fullDocument) send(ws, { type: 'admin:user:update', user: publicUser(change.fullDocument) })
      })
    } catch {}
  }

  ws.on('message', async (raw) => {
    let message: any
    try { message = JSON.parse(raw.toString()) } catch { return send(ws, { type: 'error', message: 'Invalid JSON' }) }
    const requestId = message?.requestId
    try {
      const connection: any = await realtimeDb()
      const users = connection.db.collection('users')
      const audit = connection.db.collection('admin_audit')
      const events = connection.db.collection('events')

      if (!authenticated) {
        if (message?.type !== 'auth') throw new Error('Authenticate first')
        if (message?.role === 'user') {
          const token = process.env.BOT_TOKEN?.trim()
          if (!token) throw new Error('BOT_TOKEN is not configured')
          const auth = verifyInitData(String(message?.initData || ''), token)
          if (!auth) throw new Error('Invalid Telegram initData')
          userId = String(auth.user.id)
          const now = new Date().toISOString()
          await users.updateOne({ id: userId }, { $set: {
            username: auth.user.username || '', first_name: auth.user.first_name || '', last_name: auth.user.last_name || '',
            language_code: auth.user.language_code || '', photo_url: auth.user.photo_url || '', last_seen_at: now, updated_at: now,
          }, $setOnInsert: { id: userId, joined_at: now, search_count: 0, moderation_status: 'active' } }, { upsert: true })
          authenticated = true
          role = 'user'
          if (authTimer) clearTimeout(authTimer)
          authTimer = null
          send(ws, { type: 'auth:ok', role, userId })
          await watchUser(users, userId)
          await watchEvents(events)
          return
        }
        if (message?.role === 'admin') {
          if (!verifyAdminRealtimeToken(String(message?.token || ''))) throw new Error('Invalid admin realtime token')
          authenticated = true
          role = 'admin'
          if (authTimer) clearTimeout(authTimer)
          authTimer = null
          send(ws, { type: 'auth:ok', role })
          await watchAdmin(users)
          return
        }
        throw new Error('Invalid realtime role')
      }

      if (message?.type === 'ping') return send(ws, { type: 'pong', requestId, at: Date.now() })
      if (role === 'user' && message?.type === 'moderation:get') {
        const user = await users.findOne({ id: userId })
        return send(ws, { type: 'moderation:update', requestId, user: publicUser(user), moderation: moderationSnapshot(user) })
      }
      if (role === 'admin' && message?.type === 'moderation:set') {
        const user = await applyModeration(users, audit, String(message?.userId || ''), message?.payload || {})
        return send(ws, { type: 'moderation:ack', requestId, user: publicUser(user), moderation: moderationSnapshot(user) })
      }
      throw new Error('Unknown realtime message')
    } catch (error: any) {
      send(ws, { type: 'error', requestId, message: error?.message || 'Realtime error' })
    }
  })

  ws.on('close', cleanup)
  ws.on('error', cleanup)
})

const httpServer = createHttpServer(async (req: any, res: any) => {
  try {
    restoreApiPath(req)
    nestPromise ??= createNestServer()
    const expressApp = await nestPromise
    return expressApp(req, res)
  } catch (error: any) {
    res.statusCode = 500
    res.setHeader('content-type', 'application/json')
    res.end(JSON.stringify({ message: error?.message || 'API bootstrap failed' }))
  }
})

httpServer.on('upgrade', (req, socket, head) => {
  if (!isRealtimeRequest(req)) return socket.destroy()
  wss.handleUpgrade(req, socket, head, (ws) => wss.emit('connection', ws, req))
})

export default httpServer
