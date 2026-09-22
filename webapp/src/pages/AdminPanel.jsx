import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity, AlignLeft, Ban, BellRing, Bold, CalendarDays, Check, ChevronRight, Clock3,
  Code2, Copy, Edit3, Eye, EyeOff, FileText, Gauge, Image, Italic, Languages, Link2,
  LockKeyhole, LogOut, Megaphone, Menu, MessageCircleMore, Monitor, MoreHorizontal, Plus,
  Quote, Radio, RefreshCw, RotateCcw, Search, Send, Shield, ShieldAlert, ShieldCheck,
  Smartphone, Sparkles, Strikethrough, Trash2, Underline, UserPlus, UserRound, UsersRound,
  Video, WandSparkles, Wifi, WifiOff, X,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { createRealtimeClient } from '../realtime.js'

const OWNER_ID = '8182558373'
const EMPTY_EVENT = { title: '', date: '', annual: true, category: 'history', description: '', image_url: '', hero_id: '', source_url: '', published: true }
const EMPTY_BROADCAST = {
  title: '', message: '', audience: 'all', language: '', parse_mode: 'HTML', media_type: 'none', media_url: '',
  buttons: [], silent: false, protect_content: false, link_preview: true, message_effect_id: '',
}
const STATUS_LABELS = { active: 'Active', restricted: 'Restricted', blocked: 'Blocked' }
const CATEGORY_LABELS = { birthday: 'Ծնունդ', independence: 'Պետական օր', memorial: 'Հիշատակի օր', history: 'Պատմական' }
const AUDIENCES = { all: 'All active users', active24h: 'Active · 24h', active7d: 'Active · 7d', active30d: 'Active · 30d' }
const BUTTON_TYPES = {
  url: 'Link', web_app: 'Web App', popup: 'Popup alert', copy: 'Copy text', callback: 'Callback', login_url: 'Login URL',
  switch_inline: 'Switch inline', switch_inline_current: 'Inline · current chat', switch_inline_chosen: 'Inline · choose chat',
}
const NAV = [
  ['overview', Gauge, 'Overview'], ['users', UsersRound, 'Users'], ['events', CalendarDays, 'Events'],
  ['broadcasts', Megaphone, 'Broadcast'], ['reminders', BellRing, 'Reminders'], ['team', ShieldCheck, 'Admins'],
]

function fmtDate(value, withTime = false) {
  if (!value) return '—'
  const date = new Date(value)
  if (!Number.isFinite(date.getTime())) return String(value)
  return new Intl.DateTimeFormat('hy-AM', withTime ? { dateStyle: 'medium', timeStyle: 'short' } : { dateStyle: 'medium' }).format(date)
}
function displayName(user) {
  const name = [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim()
  return name || (user?.username ? `@${user.username}` : `User ${user?.id || ''}`)
}
function StatusBadge({ status = 'active' }) {
  return <span className={`a5-status is-${status}`}>{status === 'blocked' ? <Ban size={12} /> : status === 'restricted' ? <Clock3 size={12} /> : <Check size={12} />}{STATUS_LABELS[status] || status}</span>
}
function Modal({ title, subtitle, onClose, children, size = 'md' }) {
  useEffect(() => {
    const fn = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', fn)
    return () => window.removeEventListener('keydown', fn)
  }, [onClose])
  return <div className="a5-modal-layer" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}>
    <section className={`a5-modal is-${size}`} role="dialog" aria-modal="true" aria-label={title}>
      <header><div><span>HAYOC HEROS ADMIN</span><h2>{title}</h2>{subtitle ? <p>{subtitle}</p> : null}</div><button type="button" onClick={onClose}><X size={18} /></button></header>
      <div className="a5-modal-body">{children}</div>
    </section>
  </div>
}
function Field({ label, children, hint }) { return <label className="a5-field"><span>{label}</span>{children}{hint ? <small>{hint}</small> : null}</label> }
function Button({ children, kind = 'secondary', ...props }) { return <button className={`a5-btn is-${kind}`} type="button" {...props}>{children}</button> }

function LoginScreen({ onPassword, password, setPassword, pending, error, telegramAvailable, onTelegram }) {
  const [show, setShow] = useState(false)
  return <div className="a5-login">
    <div className="a5-login-art"><div className="a5-orb one" /><div className="a5-orb two" /><div className="a5-login-brand"><div><ShieldCheck size={28} /></div><span>HAYOC HEROS</span><strong>Administration</strong></div><h1>Command the platform from one secure workspace.</h1><p>Users, events, reminders, Telegram broadcasts and realtime moderation.</p></div>
    <div className="a5-login-card"><span className="a5-kicker">SECURE ACCESS</span><h2>Admin Console</h2><p>Sign in with the admin password or your authorized Telegram account.</p>
      {telegramAvailable ? <button className="a5-telegram-login" type="button" onClick={onTelegram} disabled={pending}><Smartphone size={18} /><span><b>Continue with Telegram</b><small>Owner/admin verification via Mini App session</small></span><ChevronRight size={17} /></button> : null}
      <div className="a5-login-divider"><span>or password</span></div>
      <form onSubmit={(e) => { e.preventDefault(); onPassword() }}><Field label="Password"><div className="a5-password"><input type={show ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /><button type="button" onClick={() => setShow(v => !v)}>{show ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></Field><button className="a5-btn is-primary is-wide" disabled={pending}>{pending ? 'Signing in…' : 'Sign in'}</button></form>
      {error ? <div className="a5-error">{error}</div> : null}
      <small className="a5-owner-note">Owner Telegram ID: {OWNER_ID}</small>
    </div>
  </div>
}

function Overview({ stats, users, realtime, open }) {
  const s = stats.data || {}, u = s.users || {}, e = s.events || {}, b = s.broadcasts || {}, r = s.reminders || {}
  const cards = [
    ['users', UsersRound, u.total ?? '—', `${u.active24h || 0} active / 24h`, 'users'],
    ['moderation', ShieldAlert, (u.blocked || 0) + (u.restricted || 0), `${u.blocked || 0} blocked · ${u.restricted || 0} restricted`, 'users'],
    ['events', CalendarDays, e.total ?? '—', `${e.published || 0} published`, 'events'],
    ['broadcasts', Megaphone, b.total ?? '—', `${b.deliveries30 || 0} deliveries / 30d`, 'broadcasts'],
    ['reminders', BellRing, r.active ?? '—', `${r.due || 0} due`, 'reminders'],
  ]
  return <div className="a5-stack">
    <section className="a5-hero"><div><span className="a5-kicker"><Sparkles size={13} /> LIVE COMMAND CENTER</span><h2>Everything important, instantly visible.</h2><p>Realtime moderation, content publishing, scheduled reminders and Telegram delivery.</p><div className="a5-hero-actions"><Button kind="primary" onClick={() => open('broadcasts')}><Send size={16} /> New broadcast</Button><Button onClick={() => open('events', { add: true })}><Plus size={16} /> Add event</Button></div></div><div className={`a5-realtime is-${realtime}`}><Radio size={18} /><strong>{realtime === 'connected' ? 'Realtime online' : 'Realtime reconnecting'}</strong><span>MongoDB + WebSocket</span></div></section>
    <section className="a5-metrics">{cards.map(([key, Icon, value, sub, section]) => <button key={key} type="button" onClick={() => open(section)} className={`a5-metric is-${key}`}><span><Icon size={19} /></span><div><small>{key}</small><strong>{value}</strong><em>{sub}</em></div><ChevronRight size={16} /></button>)}</section>
    <section className="a5-panel"><div className="a5-panel-head"><div><span>RECENT ACTIVITY</span><h3>Recently active users</h3></div><Button onClick={() => open('users')}>View all</Button></div><div className="a5-user-list">{(users.data?.items || []).slice(0, 7).map((user) => <button type="button" key={user.id} onClick={() => open('users', { userId: user.id })}><div className="a5-avatar">{user.photo_url ? <img src={user.photo_url} alt="" /> : <UserRound size={18} />}</div><div><strong>{displayName(user)}</strong><small>{user.username ? `@${user.username}` : user.id}</small></div><StatusBadge status={user.moderation_status || 'active'} /><time>{fmtDate(user.last_seen_at, true)}</time></button>)}</div></section>
  </div>
}

function UsersSection({ query, setQuery, status, setStatus, users, selectedId, setSelectedId, detail, onModerate }) {
  const [mod, setMod] = useState(null)
  return <div className="a5-split is-users"><section className="a5-panel"><div className="a5-toolbar"><div className="a5-search"><Search size={16} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Name, username or Telegram ID" /></div><select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option><option value="active">Active</option><option value="restricted">Restricted</option><option value="blocked">Blocked</option></select></div><div className="a5-table-wrap"><table className="a5-table"><thead><tr><th>User</th><th>Status</th><th>Searches</th><th>Last seen</th></tr></thead><tbody>{users.data?.items?.map((u) => <tr key={u.id} className={selectedId === u.id ? 'is-selected' : ''} onClick={() => setSelectedId(u.id)}><td><div className="a5-user-cell"><div className="a5-avatar">{u.photo_url ? <img src={u.photo_url} alt="" /> : <UserRound size={17} />}</div><div><strong>{displayName(u)}</strong><small>{u.username ? `@${u.username}` : u.id}</small></div></div></td><td><StatusBadge status={u.moderation_status || 'active'} /></td><td>{u.search_count || 0}</td><td>{fmtDate(u.last_seen_at, true)}</td></tr>)}</tbody></table></div></section>
    <aside className="a5-panel a5-inspector">{!selectedId ? <div className="a5-empty"><UsersRound size={30} /><h3>Select a user</h3><p>Profile, activity and moderation tools will appear here.</p></div> : detail.isLoading ? <div className="a5-empty"><RefreshCw className="spin" size={24} /> Loading…</div> : detail.data?.user ? <><div className="a5-profile"><div className="a5-avatar xl">{detail.data.user.photo_url ? <img src={detail.data.user.photo_url} alt="" /> : <UserRound size={26} />}</div><div><h3>{displayName(detail.data.user)}</h3><p>{detail.data.user.username ? `@${detail.data.user.username}` : detail.data.user.id}</p></div><StatusBadge status={detail.data.moderation?.status || 'active'} /></div><div className="a5-facts"><div><span>Joined</span><b>{fmtDate(detail.data.user.joined_at)}</b></div><div><span>Last seen</span><b>{fmtDate(detail.data.user.last_seen_at, true)}</b></div><div><span>Searches</span><b>{detail.data.user.search_count || 0}</b></div><div><span>Language</span><b>{detail.data.user.language_code || '—'}</b></div></div><div className="a5-section-title"><span>Moderation</span></div><div className="a5-action-grid"><Button kind="danger" onClick={() => setMod({ action: 'block', title: 'Block user' })}><Ban size={15} /> Block</Button><Button onClick={() => setMod({ action: 'restrict', title: 'Restrict user' })}><Clock3 size={15} /> Restrict</Button><Button kind="success" onClick={() => onModerate({ action: 'restore' })}><RotateCcw size={15} /> Restore</Button></div><div className="a5-section-title"><span>Recent searches</span></div><div className="a5-history">{(detail.data.history || []).slice(0, 10).map((h, i) => <div key={i}><Search size={13} /><span>{h.query}</span><time>{fmtDate(h.searched_at, true)}</time></div>)}</div></> : <div className="a5-empty">User unavailable.</div>}</aside>
    {mod ? <Modal title={mod.title} subtitle="This change is applied immediately and pushed over realtime WebSocket." onClose={() => setMod(null)}><ModerationForm action={mod.action} onCancel={() => setMod(null)} onSubmit={(payload) => { onModerate(payload); setMod(null) }} /></Modal> : null}
  </div>
}
function ModerationForm({ action, onCancel, onSubmit }) {
  const [reason, setReason] = useState(''), [note, setNote] = useState(''), [duration, setDuration] = useState(1440)
  return <div className="a5-form"><Field label="Reason"><input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason shown to user" /></Field>{action === 'restrict' ? <Field label="Duration"><select value={duration} onChange={(e) => setDuration(Number(e.target.value))}><option value="60">1 hour</option><option value="1440">24 hours</option><option value="10080">7 days</option><option value="43200">30 days</option></select></Field> : null}<Field label="Internal note"><textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Visible only to admins" /></Field><div className="a5-modal-actions"><Button onClick={onCancel}>Cancel</Button><Button kind={action === 'block' ? 'danger' : 'primary'} onClick={() => onSubmit({ action, reason, note, duration_minutes: duration })}>Confirm</Button></div></div>
}

function EventModal({ event, onClose, onSave, pending }) {
  const [form, setForm] = useState(event || EMPTY_EVENT)
  const update = (key, value) => setForm((f) => ({ ...f, [key]: value }))
  return <Modal title={event?.id ? 'Update Event' : 'Add Event'} subtitle="Changes appear in the Mini App immediately through realtime invalidation." onClose={onClose} size="lg"><div className="a5-form-grid"><Field label="Title"><input value={form.title} onChange={(e) => update('title', e.target.value)} /></Field><Field label="Date"><input type="date" value={form.date} onChange={(e) => update('date', e.target.value)} /></Field><Field label="Category"><select value={form.category} onChange={(e) => update('category', e.target.value)}>{Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field><Field label="Hero ID"><input value={form.hero_id || ''} onChange={(e) => update('hero_id', e.target.value)} placeholder="Optional Mongo hero ID" /></Field><Field label="Image URL"><input value={form.image_url || ''} onChange={(e) => update('image_url', e.target.value)} placeholder="https://…" /></Field><Field label="Source URL"><input value={form.source_url || ''} onChange={(e) => update('source_url', e.target.value)} placeholder="https://…" /></Field><Field label="Description"><textarea rows="6" value={form.description || ''} onChange={(e) => update('description', e.target.value)} /></Field><div className="a5-toggles"><label><input type="checkbox" checked={form.annual !== false} onChange={(e) => update('annual', e.target.checked)} /><span>Annual recurrence</span></label><label><input type="checkbox" checked={form.published !== false} onChange={(e) => update('published', e.target.checked)} /><span>Published</span></label></div></div><div className="a5-modal-actions"><Button onClick={onClose}>Cancel</Button><Button kind="primary" disabled={pending} onClick={() => onSave(form)}>{pending ? 'Saving…' : event?.id ? 'Update Event' : 'Create Event'}</Button></div></Modal>
}
function EventsSection({ events, onAdd, onEdit, onDelete }) {
  return <section className="a5-panel"><div className="a5-panel-head"><div><span>CONTENT</span><h3>Events</h3><p>Birthdays, national dates, memorial days and historical events.</p></div><Button kind="primary" onClick={onAdd}><Plus size={16} /> Add Event</Button></div><div className="a5-card-grid">{(events.data || []).map((event) => <article className="a5-event-card" key={event.id}><div className="a5-event-date"><strong>{event.date?.slice(5) || '—'}</strong><span>{event.annual !== false ? 'Annual' : event.date?.slice(0, 4)}</span></div><div><span className="a5-chip">{CATEGORY_LABELS[event.category] || event.category}</span><h4>{event.title}</h4><p>{event.description || 'No description'}</p><small>{event.published === false ? 'Draft' : 'Published'}</small></div><div className="a5-card-actions"><button onClick={() => onEdit(event)}><Edit3 size={15} /></button><button className="danger" onClick={() => onDelete(event)}><Trash2 size={15} /></button></div></article>)}</div></section>
}

function insertFormat(textarea, form, setForm, open, close = '') {
  const el = textarea.current
  if (!el) return
  const start = el.selectionStart ?? form.message.length, end = el.selectionEnd ?? start
  const selected = form.message.slice(start, end) || 'text'
  const next = form.message.slice(0, start) + open + selected + close + form.message.slice(end)
  setForm((f) => ({ ...f, message: next }))
  requestAnimationFrame(() => { el.focus(); const pos = start + open.length + selected.length + close.length; el.setSelectionRange(pos, pos) })
}
function BroadcastButtonEditor({ buttons, setButtons }) {
  const add = () => setButtons([...buttons, { id: crypto.randomUUID?.() || String(Date.now()), row: buttons.length ? Math.max(...buttons.map(b => Number(b.row) || 0)) : 0, type: 'url', text: 'Open', value: '', popup_text: '', style: 'primary', icon_custom_emoji_id: '', chosen_chat_types: ['users'] }])
  const patch = (i, key, value) => setButtons(buttons.map((b, idx) => idx === i ? { ...b, [key]: value } : b))
  return <div className="a5-button-builder"><div className="a5-builder-head"><div><span>INLINE KEYBOARD</span><strong>Telegram buttons</strong></div><Button onClick={add}><Plus size={15} /> Add button</Button></div>{buttons.map((b, i) => <div className="a5-button-row" key={b.id || i}><input className="row" type="number" min="0" max="9" value={b.row || 0} onChange={(e) => patch(i, 'row', Number(e.target.value))} title="Row" /><select value={b.type} onChange={(e) => patch(i, 'type', e.target.value)}>{Object.entries(BUTTON_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select><input value={b.text} onChange={(e) => patch(i, 'text', e.target.value)} placeholder="Button label" /><select value={b.style || ''} onChange={(e) => patch(i, 'style', e.target.value)}><option value="">Default</option><option value="primary">Primary</option><option value="success">Success</option><option value="danger">Danger</option></select>{b.type === 'popup' ? <input className="wide" value={b.popup_text || ''} onChange={(e) => patch(i, 'popup_text', e.target.value)} placeholder="Popup alert text" /> : <input className="wide" value={b.value || ''} onChange={(e) => patch(i, 'value', e.target.value)} placeholder={b.type === 'web_app' || b.type === 'url' || b.type === 'login_url' ? 'https://…' : b.type === 'copy' ? 'Text to copy' : 'Query / callback data'} />}<input className="emoji-id" value={b.icon_custom_emoji_id || ''} onChange={(e) => patch(i, 'icon_custom_emoji_id', e.target.value)} placeholder="Button custom emoji ID" /><button className="a5-icon-danger" type="button" onClick={() => setButtons(buttons.filter((_, idx) => idx !== i))}><Trash2 size={15} /></button></div>)}{!buttons.length ? <div className="a5-empty-mini">No buttons. Add Link, Web App, Popup, Copy, Inline or Callback buttons.</div> : null}<small className="a5-builder-note">Popup buttons use callback queries. Include <code>integration/telegram_broadcast_callbacks.py</code> in your aiogram bot so Telegram can answer them with a native alert.</small></div>
}
function BroadcastSection({ campaigns, deliveries, selectedId, setSelectedId, onCreate, onUpdate, onSend, onDelete, onTest, pending }) {
  const [form, setForm] = useState(EMPTY_BROADCAST), [testId, setTestId] = useState(''), [emojiId, setEmojiId] = useState(''), [emojiFallback, setEmojiFallback] = useState('⭐')
  const textarea = useRef(null)
  useEffect(() => {
    const c = campaigns.data?.find((x) => x.id === selectedId)
    if (c) setForm({ ...EMPTY_BROADCAST, ...c, buttons: Array.isArray(c.buttons) ? c.buttons : [] })
  }, [selectedId, campaigns.data])
  const selected = campaigns.data?.find((x) => x.id === selectedId)
  const format = (open, close) => insertFormat(textarea, form, setForm, open, close)
  const saveDraft = async () => {
    const result = selectedId ? await onUpdate(selectedId, form) : await onCreate(form)
    if (result?.id) setSelectedId(result.id)
  }
  return <div className="a5-broadcast-layout"><section className="a5-panel a5-composer"><div className="a5-panel-head"><div><span>TELEGRAM STUDIO</span><h3>{selectedId ? 'Edit broadcast' : 'New broadcast'}</h3><p>Rich formatting, custom emoji, media and native Telegram inline controls.</p></div>{selectedId ? <Button onClick={() => { setSelectedId(''); setForm(EMPTY_BROADCAST) }}><Plus size={15} /> New</Button> : null}</div><div className="a5-form-grid compact"><Field label="Internal title"><input value={form.title} onChange={(e) => setForm(f => ({ ...f, title: e.target.value }))} placeholder="Campaign name" /></Field><Field label="Audience"><select value={form.audience} onChange={(e) => setForm(f => ({ ...f, audience: e.target.value }))}>{Object.entries(AUDIENCES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field><Field label="Language"><select value={form.language} onChange={(e) => setForm(f => ({ ...f, language: e.target.value }))}><option value="">All</option><option value="hy">Armenian</option><option value="en">English</option><option value="ru">Russian</option></select></Field><Field label="Parse mode"><select value={form.parse_mode} onChange={(e) => setForm(f => ({ ...f, parse_mode: e.target.value }))}><option>HTML</option><option>MarkdownV2</option><option>Markdown</option><option value="none">Plain text</option></select></Field></div><div className="a5-formatbar"><button onClick={() => format('<b>', '</b>')}><Bold size={15} /></button><button onClick={() => format('<i>', '</i>')}><Italic size={15} /></button><button onClick={() => format('<u>', '</u>')}><Underline size={15} /></button><button onClick={() => format('<s>', '</s>')}><Strikethrough size={15} /></button><button onClick={() => format('<tg-spoiler>', '</tg-spoiler>')}><EyeOff size={15} /></button><button onClick={() => format('<code>', '</code>')}><Code2 size={15} /></button><button onClick={() => format('<blockquote>', '</blockquote>')}><Quote size={15} /></button><button onClick={() => format('<blockquote expandable>', '</blockquote>')}><AlignLeft size={15} /></button><button onClick={() => format('<a href="https://example.com">', '</a>')}><Link2 size={15} /></button></div><Field label="Message"><textarea ref={textarea} className="a5-message" rows="10" value={form.message} onChange={(e) => setForm(f => ({ ...f, message: e.target.value }))} placeholder="Telegram message…" /></Field><div className="a5-custom-emoji"><div><WandSparkles size={16} /><span>Custom Emoji</span></div><input value={emojiFallback} maxLength="4" onChange={(e) => setEmojiFallback(e.target.value)} placeholder="⭐" /><input value={emojiId} onChange={(e) => setEmojiId(e.target.value)} placeholder="custom_emoji_id" /><Button onClick={() => { if (emojiId) insertFormat(textarea, form, setForm, `<tg-emoji emoji-id="${emojiId}">${emojiFallback || '⭐'}</tg-emoji>`, '') }}>Insert</Button></div><div className="a5-media-row"><Field label="Media"><select value={form.media_type} onChange={(e) => setForm(f => ({ ...f, media_type: e.target.value }))}><option value="none">No media</option><option value="photo">Photo</option><option value="video">Video</option><option value="animation">Animation / GIF</option><option value="document">Document</option></select></Field><Field label="Media URL"><input value={form.media_url} onChange={(e) => setForm(f => ({ ...f, media_url: e.target.value }))} placeholder="https://…" /></Field></div><BroadcastButtonEditor buttons={form.buttons || []} setButtons={(buttons) => setForm(f => ({ ...f, buttons }))} /><div className="a5-toggles"><label><input type="checkbox" checked={form.silent} onChange={(e) => setForm(f => ({ ...f, silent: e.target.checked }))} /><span>Silent</span></label><label><input type="checkbox" checked={form.protect_content} onChange={(e) => setForm(f => ({ ...f, protect_content: e.target.checked }))} /><span>Protect content</span></label><label><input type="checkbox" checked={form.link_preview} onChange={(e) => setForm(f => ({ ...f, link_preview: e.target.checked }))} /><span>Link preview</span></label></div><div className="a5-composer-actions"><div className="a5-test-send"><input value={testId} onChange={(e) => setTestId(e.target.value)} placeholder="Test Telegram ID" /><Button onClick={() => onTest({ ...form, user_id: testId })}><Send size={15} /> Test</Button></div><div><Button onClick={saveDraft} disabled={pending}>{selectedId ? 'Save changes' : 'Save draft'}</Button><Button kind="primary" onClick={async () => { try { const c = selectedId ? await onUpdate(selectedId, form) : await onCreate(form); const id = c?.id || selectedId; if (id) { setSelectedId(id); await onSend(id) } } catch {} }} disabled={pending}><Send size={15} /> Send broadcast</Button></div></div></section><aside className="a5-panel a5-campaigns"><div className="a5-panel-head"><div><span>CAMPAIGNS</span><h3>History</h3></div></div><div className="a5-campaign-list">{(campaigns.data || []).map((c) => <button key={c.id} className={selectedId === c.id ? 'is-selected' : ''} onClick={() => setSelectedId(c.id)}><div><strong>{c.title}</strong><small>{c.audience} · {c.parse_mode || 'HTML'}</small></div><span className={`a5-campaign-status is-${c.status}`}>{c.status}</span><em>{c.sent_count || 0}/{c.target_count || 0}</em></button>)}</div>{selected ? <div className="a5-delivery-log"><div className="a5-section-title"><span>Delivery log</span><Button kind="danger" onClick={() => onDelete(selected.id)}><Trash2 size={14} /></Button></div>{(deliveries.data || []).slice(0, 20).map((d) => <div key={d.id}><span>{d.user_id}</span><b className={d.status === 'sent' ? 'ok' : 'bad'}>{d.status}</b><small>{d.error || fmtDate(d.created_at, true)}</small></div>)}</div> : null}</aside></div>
}

function RemindersSection({ reminders, deliveries, onRun, onCancel }) {
  return <div className="a5-split"><section className="a5-panel"><div className="a5-panel-head"><div><span>AUTOMATION</span><h3>Event reminders</h3></div><Button kind="primary" onClick={onRun}><RefreshCw size={15} /> Run now</Button></div><div className="a5-table-wrap"><table className="a5-table"><thead><tr><th>User</th><th>Event</th><th>Scheduled</th><th>Status</th><th /></tr></thead><tbody>{(reminders.data || []).map((r) => <tr key={r.id}><td>{r.user_id}</td><td>{r.event_title || r.event_id}</td><td>{fmtDate(r.remind_at || r.next_reminder_at, true)}</td><td>{r.status}</td><td><button className="a5-icon-danger" onClick={() => onCancel(r.id)}><Trash2 size={14} /></button></td></tr>)}</tbody></table></div></section><aside className="a5-panel"><div className="a5-panel-head"><div><span>DELIVERIES</span><h3>Recent Telegram sends</h3></div></div><div className="a5-history">{(deliveries.data || []).slice(0, 40).map((d) => <div key={d.id}><BellRing size={13} /><span>{d.user_id} · {d.status}</span><time>{fmtDate(d.created_at, true)}</time></div>)}</div></aside></div>
}

function TeamSection({ admins, onAdd, onRemove, owner }) {
  if (!owner) return <section className="a5-panel"><div className="a5-empty"><LockKeyhole size={30} /><h3>Owner only</h3><p>Only Telegram owner {OWNER_ID} can add or remove administrators.</p></div></section>
  return <section className="a5-panel"><div className="a5-panel-head"><div><span>ACCESS CONTROL</span><h3>Admin team</h3><p>The owner account is permanent. Added admins can access the console with Telegram.</p></div><Button kind="primary" onClick={onAdd}><UserPlus size={16} /> Add Admin</Button></div><div className="a5-team-list"><article className="is-owner"><div className="a5-avatar"><ShieldCheck size={18} /></div><div><strong>Owner</strong><small>{admins.data?.owner?.telegram_id || OWNER_ID}</small></div><span>OWNER</span></article>{(admins.data?.admins || []).map((a) => <article key={a.telegram_id}><div className="a5-avatar"><UserRound size={18} /></div><div><strong>{a.name || `Admin ${a.telegram_id}`}</strong><small>{a.telegram_id}</small>{a.note ? <p>{a.note}</p> : null}</div><span>ADMIN</span><button className="a5-icon-danger" onClick={() => onRemove(a.telegram_id)}><Trash2 size={15} /></button></article>)}</div></section>
}
function AddAdminModal({ onClose, onSave, pending }) {
  const [telegram_id, setId] = useState(''), [name, setName] = useState(''), [note, setNote] = useState('')
  return <Modal title="Add administrator" subtitle="The Telegram account will be allowed to sign in to /admin through verified Mini App initData." onClose={onClose}><div className="a5-form"><Field label="Telegram user ID"><input value={telegram_id} onChange={(e) => setId(e.target.value.replace(/\D/g, ''))} placeholder="123456789" /></Field><Field label="Display name"><input value={name} onChange={(e) => setName(e.target.value)} placeholder="Admin name" /></Field><Field label="Internal note"><textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Optional" /></Field><div className="a5-modal-actions"><Button onClick={onClose}>Cancel</Button><Button kind="primary" disabled={pending || !telegram_id} onClick={() => onSave({ telegram_id, name, note })}>Add Admin</Button></div></div></Modal>
}

export default function AdminPanel() {
  const navigate = useNavigate(), qc = useQueryClient()
  const [section, setSection] = useState('overview'), [password, setPassword] = useState(''), [notice, setNotice] = useState('')
  const [userQuery, setUserQuery] = useState(''), [userStatus, setUserStatus] = useState(''), [selectedUser, setSelectedUser] = useState('')
  const [eventModal, setEventModal] = useState(null), [adminModal, setAdminModal] = useState(false), [selectedCampaign, setSelectedCampaign] = useState('')
  const [mobileMenu, setMobileMenu] = useState(false), [realtime, setRealtime] = useState('disconnected')
  const realtimeRef = useRef(null)
  const telegramAvailable = Boolean(window.Telegram?.WebApp?.initData)
  const session = useQuery({ queryKey: ['admin', 'session'], queryFn: api.adminSession, retry: false, staleTime: 10_000 })
  const authenticated = Boolean(session.data?.authenticated), owner = session.data?.session?.role === 'owner'
  const enabled = authenticated

  const stats = useQuery({ queryKey: ['admin', 'stats'], queryFn: api.adminStats, enabled, refetchInterval: 30_000 })
  const users = useQuery({ queryKey: ['admin', 'users', userQuery, userStatus], queryFn: () => api.adminUsers({ q: userQuery, status: userStatus, limit: 60 }), enabled })
  const detail = useQuery({ queryKey: ['admin', 'user', selectedUser], queryFn: () => api.adminUser(selectedUser), enabled: enabled && Boolean(selectedUser) })
  const events = useQuery({ queryKey: ['admin', 'events'], queryFn: api.adminEvents, enabled })
  const reminders = useQuery({ queryKey: ['admin', 'reminders'], queryFn: () => api.adminReminders({ limit: 120 }), enabled })
  const reminderDeliveries = useQuery({ queryKey: ['admin', 'reminder-deliveries'], queryFn: () => api.adminReminderDeliveries(100), enabled })
  const campaigns = useQuery({ queryKey: ['admin', 'broadcasts'], queryFn: api.adminBroadcasts, enabled })
  const deliveries = useQuery({ queryKey: ['admin', 'broadcast-deliveries', selectedCampaign], queryFn: () => api.adminBroadcastDeliveries(selectedCampaign, 120), enabled: enabled && Boolean(selectedCampaign) })
  const admins = useQuery({ queryKey: ['admin', 'admins'], queryFn: api.adminAdmins, enabled: enabled && owner })

  const refreshCore = async () => Promise.all([qc.invalidateQueries({ queryKey: ['admin', 'stats'] }), qc.invalidateQueries({ queryKey: ['admin', 'users'] }), qc.invalidateQueries({ queryKey: ['admin', 'events'] }), qc.invalidateQueries({ queryKey: ['admin', 'broadcasts'] })])
  const login = useMutation({ mutationFn: () => api.adminLogin(password), onSuccess: () => { setPassword(''); setNotice(''); session.refetch() }, onError: (e) => setNotice(e.message) })
  const telegramLogin = useMutation({ mutationFn: api.adminTelegramLogin, onSuccess: () => { setNotice(''); session.refetch() }, onError: (e) => setNotice(e.message) })
  const saveEvent = useMutation({ mutationFn: (form) => form.id ? api.adminUpdateEvent(form.id, form) : api.adminCreateEvent(form), onSuccess: async () => { setEventModal(null); setNotice('Event saved and public cache invalidated.'); await qc.invalidateQueries({ queryKey: ['admin', 'events'] }); qc.removeQueries({ queryKey: ['events'] }); qc.removeQueries({ queryKey: ['event'] }); stats.refetch() }, onError: (e) => setNotice(e.message) })
  const deleteEvent = useMutation({ mutationFn: api.adminDeleteEvent, onSuccess: async () => { setNotice('Event deleted.'); await qc.invalidateQueries({ queryKey: ['admin', 'events'] }); stats.refetch() } })
  const moderate = useMutation({ mutationFn: (payload) => api.adminModerateUser(selectedUser, payload), onSuccess: async () => { await Promise.all([detail.refetch(), users.refetch(), stats.refetch()]); setNotice('Moderation updated.') }, onError: (e) => setNotice(e.message) })
  const runReminders = useMutation({ mutationFn: api.adminRunReminders, onSuccess: async () => { setNotice('Reminder task completed.'); await Promise.all([reminders.refetch(), reminderDeliveries.refetch(), stats.refetch()]) } })
  const cancelReminder = useMutation({ mutationFn: api.adminCancelReminder, onSuccess: () => reminders.refetch() })
  const createBroadcast = async (form) => {
    try {
      const c = await api.adminCreateBroadcast(form)
      await campaigns.refetch(); stats.refetch(); setNotice('Broadcast draft saved.')
      return c
    } catch (e) { setNotice(`Broadcast draft failed: ${e.message}`); throw e }
  }
  const updateBroadcast = async (id, form) => {
    try {
      const c = await api.adminUpdateBroadcast(id, form)
      await campaigns.refetch(); setNotice('Broadcast updated.')
      return c
    } catch (e) { setNotice(`Broadcast update failed: ${e.message}`); throw e }
  }
  const sendBroadcast = async (id) => {
    try {
      const result = await api.adminSendBroadcast(id, 300)
      await Promise.all([campaigns.refetch(), stats.refetch(), deliveries.refetch()])
      setNotice(`Broadcast processed: ${result.sent || 0} sent · ${result.failed || 0} failed · ${result.remaining || 0} remaining.`)
      return result
    } catch (e) { setNotice(`Broadcast send failed: ${e.message}`); throw e }
  }
  const deleteBroadcast = async (id) => { try { await api.adminDeleteBroadcast(id); setSelectedCampaign(''); await campaigns.refetch(); stats.refetch() } catch (e) { setNotice(`Delete failed: ${e.message}`) } }
  const testBroadcast = async (payload) => { try { await api.adminTestBroadcast(payload); setNotice('Test message sent through Telegram Bot API.') } catch (e) { setNotice(e.message) } }
  const addAdmin = useMutation({ mutationFn: api.adminAddAdmin, onSuccess: async () => { setAdminModal(false); setNotice('Admin added.'); await admins.refetch() }, onError: (e) => setNotice(e.message) })
  const removeAdmin = useMutation({ mutationFn: api.adminRemoveAdmin, onSuccess: async () => { setNotice('Admin removed.'); await admins.refetch() }, onError: (e) => setNotice(e.message) })

  useEffect(() => {
    if (!authenticated) return
    let dead = false, client
    ;(async () => {
      try {
        const { token } = await api.adminRealtimeToken()
        if (dead) return
        client = createRealtimeClient(); realtimeRef.current = client
        client.subscribeState(setRealtime)
        client.subscribe((m) => { if (m?.type === 'admin:user:update') { qc.invalidateQueries({ queryKey: ['admin', 'users'] }); selectedUser && qc.invalidateQueries({ queryKey: ['admin', 'user', selectedUser] }) } })
        client.connect({ type: 'auth', role: 'admin', token })
      } catch { setRealtime('error') }
    })()
    return () => { dead = true; client?.close?.() }
  }, [authenticated, qc, selectedUser])

  const logout = async () => { realtimeRef.current?.close?.(); await api.adminLogout(); qc.removeQueries({ queryKey: ['admin'] }); session.refetch() }
  const open = (next, opts = {}) => { setSection(next); setMobileMenu(false); if (opts.userId) setSelectedUser(opts.userId); if (opts.add) setEventModal({ ...EMPTY_EVENT }) }

  if (session.isLoading) return <div className="a5-loading"><div /><span>Opening secure workspace…</span></div>
  if (!authenticated) return <LoginScreen password={password} setPassword={setPassword} onPassword={() => login.mutate()} onTelegram={() => telegramLogin.mutate()} pending={login.isPending || telegramLogin.isPending} error={notice} telegramAvailable={telegramAvailable} />

  const titleMap = { overview: ['Overview', 'Live health and operations'], users: ['Users', 'Search, inspect and moderate'], events: ['Events', 'Public calendar content'], broadcasts: ['Broadcast', 'Telegram delivery studio'], reminders: ['Reminders', 'Scheduled Telegram notifications'], team: ['Admins', 'Owner-managed access control'] }
  const [title, subtitle] = titleMap[section] || titleMap.overview

  return <div className="a5-shell">
    <aside className={`a5-sidebar ${mobileMenu ? 'is-open' : ''}`}><div className="a5-brand"><div><ShieldCheck size={21} /></div><span><strong>Hayoc Heros</strong><small>Admin · v5</small></span><button className="a5-mobile-close" onClick={() => setMobileMenu(false)}><X size={18} /></button></div><nav>{NAV.map(([key, Icon, label]) => key === 'team' && !owner ? null : <button key={key} className={section === key ? 'is-active' : ''} onClick={() => open(key)}><Icon size={18} /><span>{label}</span>{key === 'users' && stats.data?.users?.blocked ? <b>{stats.data.users.blocked}</b> : null}</button>)}</nav><div className="a5-side-foot"><div className={`a5-live-chip is-${realtime}`}><i /><span>{realtime === 'connected' ? 'Realtime connected' : 'Reconnecting'}</span></div><div className="a5-session-card"><Shield size={16} /><div><strong>{session.data?.session?.role === 'owner' ? 'Owner' : 'Administrator'}</strong><small>{session.data?.session?.telegram_id || session.data?.session?.auth}</small></div></div><button onClick={logout}><LogOut size={17} /> Sign out</button></div></aside>
    {mobileMenu ? <button className="a5-sidebar-scrim" onClick={() => setMobileMenu(false)} aria-label="Close menu" /> : null}
    <main className="a5-workspace"><header className="a5-topbar"><button className="a5-mobile-menu" onClick={() => setMobileMenu(true)}><Menu size={20} /></button><div><span className="a5-kicker">HAYOC HEROS · ADMIN</span><h1>{title}</h1><p>{subtitle}</p></div><div className="a5-top-actions"><span className={`a5-connection is-${realtime}`}>{realtime === 'connected' ? <Wifi size={14} /> : <WifiOff size={14} />}{realtime}</span><Button onClick={() => { refreshCore(); reminders.refetch(); campaigns.refetch(); owner && admins.refetch() }}><RefreshCw size={15} /> <span className="desktop-only">Refresh</span></Button></div></header>{notice ? <div className="a5-notice"><span>{notice}</span><button onClick={() => setNotice('')}><X size={15} /></button></div> : null}<div className="a5-content">{section === 'overview' ? <Overview stats={stats} users={users} realtime={realtime} open={open} /> : null}{section === 'users' ? <UsersSection query={userQuery} setQuery={setUserQuery} status={userStatus} setStatus={setUserStatus} users={users} selectedId={selectedUser} setSelectedId={setSelectedUser} detail={detail} onModerate={(payload) => moderate.mutate(payload)} /> : null}{section === 'events' ? <EventsSection events={events} onAdd={() => setEventModal({ ...EMPTY_EVENT })} onEdit={(event) => setEventModal({ ...event })} onDelete={(event) => window.confirm(`Delete “${event.title}”?`) && deleteEvent.mutate(event.id)} /> : null}{section === 'broadcasts' ? <BroadcastSection campaigns={campaigns} deliveries={deliveries} selectedId={selectedCampaign} setSelectedId={setSelectedCampaign} onCreate={createBroadcast} onUpdate={updateBroadcast} onSend={sendBroadcast} onDelete={deleteBroadcast} onTest={testBroadcast} pending={false} /> : null}{section === 'reminders' ? <RemindersSection reminders={reminders} deliveries={reminderDeliveries} onRun={() => runReminders.mutate()} onCancel={(id) => cancelReminder.mutate(id)} /> : null}{section === 'team' ? <TeamSection admins={admins} owner={owner} onAdd={() => setAdminModal(true)} onRemove={(id) => window.confirm(`Remove admin ${id}?`) && removeAdmin.mutate(id)} /> : null}</div></main>
    <nav className="a5-mobile-tabs">{NAV.slice(0, 5).map(([key, Icon, label]) => <button key={key} className={section === key ? 'is-active' : ''} onClick={() => open(key)}><Icon size={20} /><span>{label}</span></button>)}</nav>
    {eventModal ? <EventModal event={eventModal} onClose={() => setEventModal(null)} pending={saveEvent.isPending} onSave={(form) => saveEvent.mutate(form)} /> : null}
    {adminModal ? <AddAdminModal onClose={() => setAdminModal(false)} pending={addAdmin.isPending} onSave={(payload) => addAdmin.mutate(payload)} /> : null}
  </div>
}
