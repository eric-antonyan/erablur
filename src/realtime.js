function wsUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/realtime`
}

class RealtimeClient {
  constructor() {
    this.ws = null
    this.listeners = new Set()
    this.stateListeners = new Set()
    this.reconnectTimer = null
    this.retry = 0
    this.authPayload = null
    this.closed = false
    this.pending = new Map()
  }

  subscribe(listener) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  subscribeState(listener) {
    this.stateListeners.add(listener)
    return () => this.stateListeners.delete(listener)
  }

  emitState(state) { this.stateListeners.forEach((fn) => fn(state)) }
  emit(message) { this.listeners.forEach((fn) => fn(message)) }

  connect(authPayload) {
    this.authPayload = authPayload
    this.closed = false
    this.open()
    return this
  }

  open() {
    if (this.closed || !this.authPayload) return
    if (this.ws && [WebSocket.OPEN, WebSocket.CONNECTING].includes(this.ws.readyState)) return
    this.emitState('connecting')
    const socket = new WebSocket(wsUrl())
    this.ws = socket

    socket.addEventListener('open', () => {
      this.retry = 0
      this.emitState('connected')
      socket.send(JSON.stringify(this.authPayload))
    })
    socket.addEventListener('message', (event) => {
      let message
      try { message = JSON.parse(event.data) } catch { return }
      if (message?.requestId && this.pending.has(message.requestId)) {
        const task = this.pending.get(message.requestId)
        this.pending.delete(message.requestId)
        if (message.type === 'error') task.reject(new Error(message.message || 'Realtime request failed'))
        else task.resolve(message)
      }
      this.emit(message)
    })
    socket.addEventListener('close', () => {
      this.emitState('disconnected')
      this.ws = null
      if (this.closed) return
      const wait = Math.min(15_000, 700 * 2 ** Math.min(this.retry++, 5))
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = setTimeout(() => this.open(), wait)
    })
    socket.addEventListener('error', () => this.emitState('error'))
  }

  send(type, payload = {}, timeoutMs = 7000) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return Promise.reject(new Error('Realtime connection unavailable'))
    const requestId = `${Date.now()}-${Math.random().toString(36).slice(2)}`
    const packet = { type, requestId, ...payload }
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(requestId)
        reject(new Error('Realtime request timed out'))
      }, timeoutMs)
      this.pending.set(requestId, {
        resolve: (value) => { clearTimeout(timer); resolve(value) },
        reject: (error) => { clearTimeout(timer); reject(error) },
      })
      this.ws.send(JSON.stringify(packet))
    })
  }

  close() {
    this.closed = true
    clearTimeout(this.reconnectTimer)
    this.pending.forEach(({ reject }) => reject(new Error('Realtime connection closed')))
    this.pending.clear()
    try { this.ws?.close() } catch {}
    this.ws = null
  }
}

export function createRealtimeClient() { return new RealtimeClient() }
