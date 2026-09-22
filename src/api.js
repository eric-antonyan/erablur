const API_BASE = '/api'

function initData() {
  return window.Telegram?.WebApp?.initData || ''
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {})
  headers.set('Accept', 'application/json')
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const tg = initData()
  if (tg) headers.set('X-Telegram-Init-Data', tg)

  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'same-origin',
    cache: options.cache || 'default',
    ...options,
    headers,
  })

  if (!response.ok) {
    let message = `HTTP ${response.status}`
    let data = null
    try {
      data = await response.json()
      message = data?.message || data?.error || message
    } catch {}
    const error = new Error(Array.isArray(message) ? message.join(', ') : message)
    error.status = response.status
    error.data = data
    throw error
  }
  if (response.status === 204) return null
  return response.json()
}

export const api = {
  meta: () => request('/meta'),
  random: (limit = 6) => request(`/heroes/random?limit=${limit}`),
  heroes: ({ q = '', war = '', region = '', page = 1, limit = 18 } = {}) => {
    const params = new URLSearchParams({ page: String(page), limit: String(limit) })
    if (q) params.set('q', q)
    if (war) params.set('war', war)
    if (region) params.set('region', region)
    return request(`/heroes?${params.toString()}`)
  },
  hero: (id) => request(`/heroes/${encodeURIComponent(id)}`),
  events: ({ from = '', to = '', limit = 100 } = {}) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (from) params.set('from', from)
    if (to) params.set('to', to)
    return request(`/events?${params.toString()}`, { cache: 'no-store' })
  },
  upcomingEvents: (limit = 8) => request(`/events/upcoming?limit=${limit}`, { cache: 'no-store' }),
  event: (id) => request(`/events/${encodeURIComponent(id)}`, { cache: 'no-store' }),
  me: () => request('/me'),
  logHistory: (payload) => request('/history', { method: 'POST', body: JSON.stringify(payload) }),
  clearHistory: () => request('/history', { method: 'DELETE' }),
  reminders: () => request('/reminders'),
  eventReminder: (eventId) => request(`/reminders/event/${encodeURIComponent(eventId)}`),
  saveEventReminder: (eventId, payload) => request(`/reminders/event/${encodeURIComponent(eventId)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  cancelEventReminder: (eventId) => request(`/reminders/event/${encodeURIComponent(eventId)}`, { method: 'DELETE' }),

  adminSession: () => request('/admin/session'),
  adminLogin: (password) => request('/admin/login', { method: 'POST', body: JSON.stringify({ password }) }),
  adminTelegramLogin: () => request('/admin/telegram-login', { method: 'POST' }),
  adminLogout: () => request('/admin/logout', { method: 'POST' }),
  adminAdmins: () => request('/admin/admins'),
  adminAddAdmin: (payload) => request('/admin/admins', { method: 'POST', body: JSON.stringify(payload) }),
  adminRemoveAdmin: (telegramId) => request(`/admin/admins/${encodeURIComponent(telegramId)}`, { method: 'DELETE' }),
  adminStats: () => request('/admin/stats'),
  adminRealtimeToken: () => request('/admin/realtime-token'),
  adminUsers: ({ q = '', status = '', page = 1, limit = 30 } = {}) => {
    const params = new URLSearchParams({ page: String(page), limit: String(limit) })
    if (q) params.set('q', q)
    if (status) params.set('status', status)
    return request(`/admin/users?${params.toString()}`)
  },
  adminUser: (id) => request(`/admin/users/${encodeURIComponent(id)}`),
  adminModerateUser: (id, payload) => request(`/admin/users/${encodeURIComponent(id)}/moderation`, { method: 'PATCH', body: JSON.stringify(payload) }),
  adminClearUserHistory: (id) => request(`/admin/users/${encodeURIComponent(id)}/history`, { method: 'DELETE' }),
  adminEvents: () => request('/admin/events'),
  adminCreateEvent: (payload) => request('/admin/events', { method: 'POST', body: JSON.stringify(payload) }),
  adminUpdateEvent: (id, payload) => request(`/admin/events/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  adminDeleteEvent: (id) => request(`/admin/events/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  adminReminders: ({ status = '', limit = 100 } = {}) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (status) params.set('status', status)
    return request(`/admin/reminders?${params.toString()}`)
  },
  adminReminderDeliveries: (limit = 80) => request(`/admin/reminder-deliveries?limit=${limit}`),
  adminRunReminders: () => request('/admin/reminders/run', { method: 'POST' }),
  adminCancelReminder: (id) => request(`/admin/reminders/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  adminBroadcasts: () => request('/admin/broadcasts'),
  adminBroadcastDeliveries: (id, limit = 100) => request(`/admin/broadcasts/${encodeURIComponent(id)}/deliveries?limit=${limit}`),
  adminCreateBroadcast: (payload) => request('/admin/broadcasts', { method: 'POST', body: JSON.stringify(payload) }),
  adminUpdateBroadcast: (id, payload) => request(`/admin/broadcasts/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  adminTestBroadcast: (payload) => request('/admin/broadcasts/test', { method: 'POST', body: JSON.stringify(payload) }),
  adminSendBroadcast: (id, max = 300) => request(`/admin/broadcasts/${encodeURIComponent(id)}/send`, { method: 'POST', body: JSON.stringify({ max }) }),
  adminDeleteBroadcast: (id) => request(`/admin/broadcasts/${encodeURIComponent(id)}`, { method: 'DELETE' }),
}
