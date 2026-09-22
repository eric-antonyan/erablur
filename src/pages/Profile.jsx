import { useMutation, useQueryClient } from '@tanstack/react-query'
import { BellRing, Clock3, Eraser, ExternalLink, Search, Trash2, UserRound } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import GlassCard from '../components/GlassCard.jsx'
import { useMeQuery, useRemindersQuery } from '../queries.js'

function dateLabel(value) {
  if (!value) return '—'
  const date = new Date(`${value}T12:00:00`)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('hy-AM', { day: 'numeric', month: 'long', year: 'numeric' }).format(date)
}

export default function Profile({ tg }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const dataQuery = useMeQuery(tg.isTelegram)
  const reminders = useRemindersQuery(tg.isTelegram)
  const data = dataQuery.data
  const user = data?.user
  const display = [tg.user?.first_name || user?.first_name, tg.user?.last_name || user?.last_name].filter(Boolean).join(' ') || 'Telegram օգտատեր'

  const cancel = useMutation({
    mutationFn: (eventId) => api.cancelEventReminder(eventId),
    onSuccess: async () => {
      tg.notify('success')
      await queryClient.invalidateQueries({ queryKey: ['reminders'] })
    },
  })

  if (!tg.isTelegram) {
    const bot = import.meta.env.VITE_BOT_USERNAME || 'erablurbot'
    return <div className="page profile-page"><header className="simple-header"><div><div className="eyebrow">ԻՄ ԷՋԸ</div><h1>Պրոֆիլ</h1></div></header><GlassCard className="telegram-required"><div className="profile-placeholder"><UserRound size={30} /></div><h2>Բացիր Telegram-ում</h2><p>Պրոֆիլը, հիշեցումները և որոնումների պատմությունը հասանելի են Telegram Mini App-ում՝ Telegram initData անվտանգ ստուգմամբ։</p><a className="primary-button" href={`https://t.me/${bot}`}><ExternalLink size={17} /> Բացել բոտը</a></GlassCard></div>
  }

  return (
    <div className="page profile-page">
      <header className="simple-header"><div><div className="eyebrow">ԻՄ ԷՋԸ</div><h1>Պրոֆիլ</h1></div></header>
      <GlassCard className="profile-card">
        <div className="profile-avatar">{tg.user?.photo_url ? <img src={tg.user.photo_url} alt="" /> : <span>{display[0]}</span>}</div>
        <div className="profile-info"><h2>{display}</h2><p>{tg.user?.username ? `@${tg.user.username}` : 'Telegram օգտատեր'}</p></div>
        <div className="profile-search-count"><strong>{user?.search_count ?? '—'}</strong><span>որոնում</span></div>
      </GlassCard>

      <section className="section-block">
        <div className="section-heading"><div><span className="section-kicker">ՀԻՇԵՑՈՒՄՆԵՐ</span><h2>Իմ առաջիկա հիշեցումները</h2></div></div>
        {reminders.isLoading ? <div className="skeleton history-skeleton" /> : reminders.data?.items?.length ? <GlassCard className="profile-reminders-card">{reminders.data.items.map((item) => <div className="profile-reminder-item" key={item.id}><button type="button" onClick={() => navigate(`/event/${item.event_id}`)}><span className="history-icon"><BellRing size={17} /></span><span className="history-copy"><strong>{item.event_title || 'Իրադարձություն'}</strong><small>{dateLabel(item.next_occurrence)} · {item.offset_days === 0 ? 'նույն օրը' : `${item.offset_days} օր առաջ`}</small></span></button><button type="button" className="profile-reminder-delete" aria-label="Անջատել հիշեցումը" onClick={() => cancel.mutate(item.event_id)}><Trash2 size={16} /></button></div>)}</GlassCard> : <GlassCard className="empty-history"><BellRing size={23} /><strong>Հիշեցումներ դեռ չկան</strong><span>Բացիր Օրացույցը և ընտրիր այն օրերը, որոնց մասին ուզում ես Telegram հիշեցում ստանալ։</span></GlassCard>}
      </section>

      <section className="section-block">
        <div className="section-heading"><div><span className="section-kicker">ՊԱՏՄՈՒԹՅՈՒՆ</span><h2>Վերջին որոնումները</h2></div>{data?.recent?.length ? <button type="button" className="text-button danger-text" onClick={async () => { tg.haptic('medium'); await api.clearHistory(); tg.notify('success'); queryClient.invalidateQueries({ queryKey: ['me'] }) }}><Eraser size={15} /> Մաքրել</button> : null}</div>
        {dataQuery.isLoading ? <div className="skeleton history-skeleton" /> : data?.recent?.length ? <GlassCard className="history-card">{data.recent.map((item, index) => <button type="button" key={`${item.searched_at}-${index}`} className="history-item" onClick={() => item.hero_id ? navigate(`/hero/${item.hero_id}`) : navigate(`/museum?q=${encodeURIComponent(item.query)}`)}><span className="history-icon"><Clock3 size={17} /></span><span className="history-copy"><strong>{item.hero_name || item.query}</strong><small>{item.query}</small></span><Search size={16} /></button>)}</GlassCard> : <GlassCard className="empty-history"><Search size={23} /><strong>Դեռ որոնումներ չկան</strong><span>Բացահայտիր թանգարանը և այստեղ կտեսնես վերջին որոնումները։</span></GlassCard>}
      </section>
    </div>
  )
}
