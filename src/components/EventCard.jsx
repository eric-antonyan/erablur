import { CalendarDays, ChevronRight, Flag, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'

const categoryIcon = { birthday: Sparkles, independence: Flag, history: CalendarDays, memorial: CalendarDays }

export function eventDateLabel(event) {
  const value = event?.next_date || event?.date
  if (!value) return '—'
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('hy-AM', { day: 'numeric', month: 'long', year: 'numeric' }).format(date)
}

export default function EventCard({ event, onClick, compact = false }) {
  const Icon = categoryIcon[event?.category] || CalendarDays
  return (
    <motion.button type="button" className={`event-card ${compact ? 'event-card--compact' : ''}`} onClick={onClick} whileTap={{ scale: .985 }}>
      {event?.image_url ? <div className="event-card__image"><img src={event.image_url} alt="" loading="lazy" /></div> : null}
      <div className="event-card__date"><Icon size={16} /><span>{eventDateLabel(event)}</span>{event?.annual ? <b>ամեն տարի</b> : null}</div>
      <strong>{event?.title}</strong>
      {!compact && event?.description ? <p>{event.description}</p> : null}
      <span className="event-card__open">Բացել <ChevronRight size={15} /></span>
    </motion.button>
  )
}
