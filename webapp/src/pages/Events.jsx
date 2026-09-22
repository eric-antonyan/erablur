import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CalendarDays, Filter } from 'lucide-react'
import EventCard from '../components/EventCard.jsx'
import GlassCard from '../components/GlassCard.jsx'
import { useEventsQuery } from '../queries.js'

const CATEGORIES = [
  ['all', 'Բոլորը'],
  ['birthday', 'Ծնունդներ'],
  ['independence', 'Պետական օրեր'],
  ['memorial', 'Հիշատակի օրեր'],
  ['history', 'Պատմական'],
]

export default function Events({ tg }) {
  const navigate = useNavigate()
  const events = useEventsQuery()
  const [category, setCategory] = useState('all')
  const items = useMemo(() => {
    const source = events.data?.items || []
    return category === 'all' ? source : source.filter((item) => item.category === category)
  }, [events.data, category])

  return (
    <div className="page events-page">
      <header className="simple-header">
        <div><div className="eyebrow">ՀԻՇԱՐԺԱՆ ՕՐԵՐ</div><h1>Օրացույց</h1></div>
        <span className="header-symbol"><CalendarDays size={21} /></span>
      </header>

      <GlassCard className="events-intro">
        <div className="events-intro__icon"><CalendarDays size={23} /></div>
        <div><strong>Պատմությունը նաև օրացույց է</strong><p>Ծննդյան օրեր, պետական տոներ, հիշատակի և պատմական կարևոր ամսաթվեր։</p></div>
      </GlassCard>

      <div className="filter-inline"><Filter size={15} /><span>Ֆիլտրել</span></div>
      <div className="chip-scroll event-categories">
        {CATEGORIES.map(([id, label]) => <button type="button" key={id} className={`chip ${category === id ? 'is-active' : ''}`} onClick={() => { tg.selection(); setCategory(id) }}>{label}</button>)}
      </div>

      {events.isLoading ? <div className="event-list"><div className="skeleton event-list-skeleton" /><div className="skeleton event-list-skeleton" /></div> : events.isError ? <GlassCard className="message-card">Չհաջողվեց բեռնել իրադարձությունները։</GlassCard> : items.length ? (
        <div className="event-list">{items.map((event) => <EventCard key={event.id} event={event} onClick={() => { tg.haptic('light'); navigate(`/event/${event.id}`) }} />)}</div>
      ) : <GlassCard className="empty-state"><CalendarDays size={25} /><strong>Այս բաժնում դեռ իրադարձություններ չկան</strong><span>Նոր իրադարձությունները կհայտնվեն այստեղ։</span></GlassCard>}
    </div>
  )
}
