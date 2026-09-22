import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowUpRight, CalendarDays, ChevronRight, Heart, Search, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'
import { api } from '../api.js'
import EventCard from '../components/EventCard.jsx'
import GlassCard from '../components/GlassCard.jsx'
import HeroCard from '../components/HeroCard.jsx'
import SearchField from '../components/SearchField.jsx'
import { LoadingCards } from '../components/Loading.jsx'
import { heroName } from '../lib.js'
import { useMetaQuery, useRandomHeroesQuery, useUpcomingEventsQuery } from '../queries.js'

export default function Home({ tg }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [query, setQuery] = useState('')
  const meta = useMetaQuery()
  const random = useRandomHeroesQuery(6)
  const events = useUpcomingEventsQuery(3)
  const hero = meta.data?.heroOfDay
  const firstName = tg.user?.first_name || 'բարեկամ'

  const search = () => {
    tg.haptic('light')
    navigate(`/museum${query.trim() ? `?q=${encodeURIComponent(query.trim())}` : ''}`)
  }

  const openHero = (item) => {
    tg.haptic('light')
    navigate(`/hero/${encodeURIComponent(item.id)}`)
  }

  const prefetchHero = (item) => {
    if (!item?.id) return
    queryClient.prefetchQuery({ queryKey: ['hero', item.id], queryFn: () => api.hero(item.id), staleTime: 30 * 60_000 })
  }

  return (
    <div className="page home-page">
      <header className="topbar">
        <div>
          <div className="eyebrow">ՀԱՅՈՑ ՀԵՐՈՍՆԵՐ</div>
          <h1>Բարի գալուստ, {firstName}</h1>
        </div>
      </header>

      <motion.section className="cinematic-banner" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .42 }}>
        <div className="cinematic-banner__media">
          {hero?.img_url ? <img src={hero.img_url} alt={heroName(hero)} fetchPriority="high" /> : null}
          <div className="cinematic-banner__wash" />
          <div className="cinematic-banner__grain" />
        </div>
        <div className="cinematic-banner__content">
          <div className="banner-topline"><span><Sparkles size={14} /> Օրվա հերոսը</span><span>{meta.data?.count ? `${meta.data.count.toLocaleString('hy-AM')} պատմություն` : 'Թվային հիշողություն'}</span></div>
          <div className="banner-copy">
            <div className="tricolor-line"><i /><i /><i /></div>
            <h2>{hero ? heroName(hero) : 'Հիշողությունը ապրում է, երբ պատմվում է։'}</h2>
            <p>{hero ? [hero.region, hero.war].filter(Boolean).join(' · ') : 'Հայ հերոսների պատմությունները՝ մեկ ժամանակակից թվային թանգարանում։'}</p>
          </div>
          <div className="banner-actions">
            <button type="button" className="banner-primary" disabled={!hero} onClick={() => hero && openHero(hero)}>Բացել պատմությունը <ArrowUpRight size={17} /></button>
            <button type="button" className="banner-round" onClick={() => navigate('/events')} aria-label="Իրադարձություններ"><CalendarDays size={18} /></button>
          </div>
        </div>
      </motion.section>

      <div className="home-search-wrap">
        <SearchField value={query} onChange={setQuery} onSubmit={search} placeholder="Փնտրել անուն, ազգանուն, մարզ…" />
      </div>

      <section className="home-metrics">
        <button type="button" onClick={() => navigate('/museum')}><strong>{meta.data?.count?.toLocaleString('hy-AM') || '—'}</strong><span>հերոս</span></button>
        <button type="button" onClick={() => navigate('/events')}><strong>{events.data?.length ?? '—'}</strong><span>մոտակա օր</span></button>
        <button type="button" onClick={() => navigate('/museum?focus=search')}><Search size={19} /><span>արագ որոնում</span></button>
      </section>

      <section className="section-block">
        <div className="section-heading">
          <div><span className="section-kicker">ՄՈՏԱԿԱ ՕՐԵՐ</span><h2>Հիշարժան իրադարձություններ</h2></div>
          <button type="button" className="text-button" onClick={() => navigate('/events')}>Օրացույց <ChevronRight size={17} /></button>
        </div>
        <div className="event-strip">
          {events.isLoading ? <div className="skeleton event-strip-skeleton" /> : events.data?.length ? events.data.map((event) => <EventCard key={event.id} compact event={event} onClick={() => navigate(`/event/${event.id}`)} />) : <GlassCard className="message-card">Իրադարձությունները շուտով կհայտնվեն այստեղ։</GlassCard>}
        </div>
      </section>

      <section className="section-block">
        <div className="section-heading">
          <div><span className="section-kicker">ԲԱՑԱՀԱՅՏԻՐ</span><h2>Այլ պատմություններ</h2></div>
          <button type="button" className="text-button" onClick={() => random.refetch()}>Թարմացնել</button>
        </div>
        {random.isError ? <GlassCard className="message-card">Չհաջողվեց բեռնել հերոսներին։</GlassCard> : random.data?.length ? (
          <div className="hero-grid">{random.data.map((item) => <HeroCard key={item.id} hero={item} onClick={() => openHero(item)} onPrefetch={() => prefetchHero(item)} />)}</div>
        ) : <LoadingCards />}
      </section>

      <GlassCard className="memory-note">
        <Heart size={19} /><p>Յուրաքանչյուր անուն՝ կյանք։ Յուրաքանչյուր պատմություն՝ հիշողություն։</p>
      </GlassCard>
    </div>
  )
}
