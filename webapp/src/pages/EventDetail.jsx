import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { Bell, BellOff, BellRing, CalendarDays, ExternalLink, Link2, Repeat2, UserRound } from 'lucide-react'
import { eventDateLabel } from '../components/EventCard.jsx'
import GlassCard from '../components/GlassCard.jsx'
import { PageLoader } from '../components/Loading.jsx'
import { api } from '../api.js'
import { useEventQuery, useEventReminderQuery } from '../queries.js'

const OFFSETS = [
  { value: 0, label: 'Նույն օրը' },
  { value: 1, label: '1 օր առաջ' },
  { value: 3, label: '3 օր առաջ' },
  { value: 7, label: '7 օր առաջ' },
  { value: 14, label: '14 օր առաջ' },
]

function reminderLabel(reminder) {
  if (!reminder) return 'Հիշեցումը միացված չէ'
  const option = OFFSETS.find((item) => item.value === reminder.offset_days)
  return `${option?.label || `${reminder.offset_days} օր առաջ`} · մոտ 09:00`
}

export default function EventDetail({ tg }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const query = useEventQuery(id)
  const reminderQuery = useEventReminderQuery(id, tg.isTelegram)
  const [offsetDays, setOffsetDays] = useState(1)
  const [message, setMessage] = useState('')
  const event = query.data
  const reminder = reminderQuery.data?.reminder || null

  useEffect(() => {
    if (reminder && Number.isFinite(Number(reminder.offset_days))) setOffsetDays(Number(reminder.offset_days))
  }, [reminder?.id, reminder?.offset_days])

  const saveReminder = useMutation({
    mutationFn: async () => {
      if (tg.capabilities?.writeAccess) {
        try { await tg.requestWriteAccess() } catch {}
      }
      return api.saveEventReminder(id, { offset_days: offsetDays })
    },
    onSuccess: async () => {
      tg.notify('success')
      setMessage('Հիշեցումը միացված է։ Telegram-ում ծանուցում կստանաս ընտրված օրը։')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['reminder', 'event', id] }),
        queryClient.invalidateQueries({ queryKey: ['reminders'] }),
      ])
    },
    onError: (error) => {
      tg.notify('error')
      setMessage(error?.message || 'Չհաջողվեց միացնել հիշեցումը։')
    },
  })

  const cancelReminder = useMutation({
    mutationFn: () => api.cancelEventReminder(id),
    onSuccess: async () => {
      tg.notify('success')
      setMessage('Հիշեցումը անջատված է։')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['reminder', 'event', id] }),
        queryClient.invalidateQueries({ queryKey: ['reminders'] }),
      ])
    },
  })

  if (query.isLoading) return <div className="page"><PageLoader /></div>
  if (query.isError || !event) return <div className="page"><GlassCard className="message-card">Իրադարձությունը չի գտնվել։</GlassCard></div>

  const share = () => tg.share(`${window.location.origin}/event/${event.id}`, `${event.title} — Հայոց Հերոսներ`)

  return (
    <div className="event-detail-page">
      <div className={`event-detail-hero ${event.image_url ? 'has-image' : ''}`}>
        {event.image_url ? <img src={event.image_url} alt="" /> : <CalendarDays size={54} />}
        <div className="event-detail-hero__shade" />
      </div>
      <article className="event-detail-sheet">
        <div className="sheet-handle" />
        <span className="detail-kicker">ՀԻՇԱՐԺԱՆ ՕՐ</span>
        <h1>{event.title}</h1>
        <div className="event-detail-date"><CalendarDays size={18} /><strong>{eventDateLabel(event)}</strong>{event.annual ? <span><Repeat2 size={14} /> ամեն տարի</span> : null}</div>
        {event.description ? <p className="event-detail-description">{event.description}</p> : <p className="event-detail-description muted">Նկարագրությունը դեռ չի լրացվել։</p>}

        <section className="event-reminder-card">
          <div className="event-reminder-card__head">
            <span className={`event-reminder-icon ${reminder ? 'is-active' : ''}`}>{reminder ? <BellRing size={19} /> : <Bell size={19} />}</span>
            <div><span>TELEGRAM REMINDER</span><h2>{reminder ? 'Հիշեցումը միացված է' : 'Չմոռանալ այս օրը'}</h2><p>{reminderLabel(reminder)}</p></div>
          </div>
          {tg.isTelegram ? (
            <>
              <div className="reminder-offset-grid">
                {OFFSETS.map((item) => <button type="button" key={item.value} className={offsetDays === item.value ? 'is-active' : ''} onClick={() => { tg.selection(); setOffsetDays(item.value) }}>{item.label}</button>)}
              </div>
              <div className="event-reminder-actions">
                <button type="button" className="primary-button" disabled={saveReminder.isPending} onClick={() => saveReminder.mutate()}><BellRing size={17} /> {reminder ? 'Թարմացնել հիշեցումը' : 'Միացնել հիշեցումը'}</button>
                {reminder ? <button type="button" className="secondary-button danger-text" disabled={cancelReminder.isPending} onClick={() => cancelReminder.mutate()}><BellOff size={17} /> Անջատել</button> : null}
              </div>
              <small className="reminder-task-note">Հիշեցումները ուղարկվում են Telegram բոտով՝ մոտավորապես 09:00-ին Երևանի ժամանակով։</small>
            </>
          ) : <p className="reminder-telegram-only">Հիշեցումներ միացնելու համար բացիր այս էջը Telegram Mini App-ում։</p>}
          {message ? <div className="reminder-inline-message">{message}</div> : null}
        </section>

        <div className="event-detail-links">
          {event.hero_id ? <button type="button" className="secondary-button" onClick={() => navigate(`/hero/${encodeURIComponent(event.hero_id)}`)}><UserRound size={17} /> Բացել կապված հերոսին</button> : null}
          {event.source_url ? <button type="button" className="secondary-button" onClick={() => tg.webApp?.openLink ? tg.webApp.openLink(event.source_url) : window.open(event.source_url, '_blank', 'noopener,noreferrer')}><ExternalLink size={17} /> Սկզբնաղբյուր</button> : null}
          <button type="button" className="primary-button" onClick={share}><Link2 size={17} /> Կիսվել</button>
        </div>
      </article>
    </div>
  )
}
