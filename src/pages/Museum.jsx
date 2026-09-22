import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Search, SlidersHorizontal, X } from 'lucide-react'
import { api } from '../api.js'
import GlassCard from '../components/GlassCard.jsx'
import HeroCard from '../components/HeroCard.jsx'
import SearchField from '../components/SearchField.jsx'
import { LoadingCards } from '../components/Loading.jsx'
import { useHeroesInfiniteQuery, useMetaQuery } from '../queries.js'

export default function Museum({ tg }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [params, setParams] = useSearchParams()
  const [query, setQuery] = useState(params.get('q') || '')
  const [submitted, setSubmitted] = useState(params.get('q') || '')
  const [war, setWar] = useState(params.get('war') || '')
  const [region, setRegion] = useState(params.get('region') || '')
  const [showFilters, setShowFilters] = useState(false)
  const meta = useMetaQuery()
  const heroes = useHeroesInfiniteQuery({ q: submitted, war, region, limit: 18 })

  useEffect(() => {
    const timer = window.setTimeout(() => setSubmitted(query.trim()), 300)
    return () => window.clearTimeout(timer)
  }, [query])

  useEffect(() => {
    const next = {}
    if (submitted) next.q = submitted
    if (war) next.war = war
    if (region) next.region = region
    setParams(next, { replace: true })
  }, [submitted, war, region])

  const items = heroes.data?.pages.flatMap((page) => page.items || []) || []
  const pagination = heroes.data?.pages?.[heroes.data.pages.length - 1]?.pagination
  const activeCount = Number(Boolean(war)) + Number(Boolean(region))
  const title = useMemo(() => submitted ? `«${submitted}»` : 'Բոլոր հերոսները', [submitted])
  const filters = meta.data?.filters || { wars: [], regions: [] }

  const prefetchHero = (hero) => {
    if (!hero?.id) return
    queryClient.prefetchQuery({ queryKey: ['hero', hero.id], queryFn: () => api.hero(hero.id), staleTime: 30 * 60_000 })
  }

  return (
    <div className="page museum-page">
      <header className="simple-header">
        <div><div className="eyebrow">ԹՎԱՅԻՆ ԹԱՆԳԱՐԱՆ</div><h1>{title}</h1></div>
      </header>

      <SearchField value={query} onChange={setQuery} onSubmit={() => { tg.haptic('light'); setSubmitted(query.trim()) }} onClear={() => setSubmitted('')} autoFocus={params.get('focus') === 'search'} />
      <button type="button" className={`museum-filter-trigger ${activeCount ? 'has-badge' : ''}`} onClick={() => setShowFilters((v) => !v)}><span><SlidersHorizontal size={17} /> Ֆիլտրեր</span>{activeCount ? <b>{activeCount}</b> : <small>{showFilters ? 'Փակել' : 'Բացել'}</small>}</button>

      {showFilters ? <GlassCard className="filters-panel">
        <div className="filter-title"><strong>Ֆիլտրեր</strong><button type="button" className="icon-button icon-button--small" onClick={() => setShowFilters(false)}><X size={16} /></button></div>
        <label>Պատերազմ / բաժին</label>
        <div className="chip-scroll"><button type="button" className={`chip ${!war ? 'is-active' : ''}`} onClick={() => setWar('')}>Բոլորը</button>{filters.wars.map((value) => <button type="button" key={value} className={`chip ${war === value ? 'is-active' : ''}`} onClick={() => { tg.selection(); setWar(value) }}>{value}</button>)}</div>
        <label>Մարզ</label>
        <div className="chip-scroll"><button type="button" className={`chip ${!region ? 'is-active' : ''}`} onClick={() => setRegion('')}>Բոլորը</button>{filters.regions.map((value) => <button type="button" key={value} className={`chip ${region === value ? 'is-active' : ''}`} onClick={() => { tg.selection(); setRegion(value) }}>{value}</button>)}</div>
      </GlassCard> : null}

      <div className="result-summary">
        <span>{heroes.isLoading && !pagination ? 'Որոնում…' : pagination ? `${pagination.total.toLocaleString('hy-AM')} արդյունք` : '—'}</span>
        {(war || region) ? <button type="button" onClick={() => { setWar(''); setRegion('') }}>Մաքրել ֆիլտրերը</button> : null}
      </div>

      {heroes.isError ? <GlassCard className="message-card">Չհաջողվեց բեռնել հերոսներին։ <button type="button" className="text-button" onClick={() => heroes.refetch()}>Կրկին</button></GlassCard> : null}
      {heroes.isLoading ? <LoadingCards count={8} /> : <div className="hero-grid">{items.map((hero) => <HeroCard key={hero.id} hero={hero} onPrefetch={() => prefetchHero(hero)} onClick={() => navigate(`/hero/${encodeURIComponent(hero.id)}`, { state: { query: submitted } })} />)}</div>}

      {!heroes.isLoading && !items.length && !heroes.isError ? <GlassCard className="empty-state"><div className="empty-icon"><Search size={24} /></div><strong>Ոչինչ չգտնվեց</strong><span>Փորձիր անունը, ազգանունը, մարզը կամ պատերազմի անվանումը։</span></GlassCard> : null}
      {heroes.hasNextPage ? <button type="button" className="primary-button load-more" disabled={heroes.isFetchingNextPage} onClick={() => heroes.fetchNextPage()}>{heroes.isFetchingNextPage ? 'Բեռնվում է…' : 'Ցույց տալ ավելին'}</button> : null}
    </div>
  )
}
