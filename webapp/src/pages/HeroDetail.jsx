import { useEffect } from 'react'
import { useLocation, useParams } from 'react-router-dom'
import { CalendarDays, ExternalLink, MapPin, Share2, Shield, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'
import { api } from '../api.js'
import GlassCard from '../components/GlassCard.jsx'
import { PageLoader } from '../components/Loading.jsx'
import { biographyParagraphs, cleanText, formatLife, heroBirth, heroDeath, heroName, initials } from '../lib.js'
import { useHeroQuery } from '../queries.js'

export default function HeroDetail({ tg }) {
  const { id } = useParams()
  const location = useLocation()
  const heroQuery = useHeroQuery(id)
  const hero = heroQuery.data

  useEffect(() => {
    if (!hero || !tg.isTelegram) return
    api.logHistory({ query: location.state?.query || heroName(hero), heroId: hero.id, heroName: heroName(hero) }).catch(() => {})
  }, [hero?.id])

  const share = () => {
    if (!hero) return
    tg.haptic('medium')
    tg.share(`${window.location.origin}/hero/${encodeURIComponent(hero.id)}`, `${heroName(hero)} — Հայոց Հերոսներ`)
  }


  if (heroQuery.isLoading) return <div className="page"><PageLoader /></div>
  if (heroQuery.isError || !hero) return (
    <div className="page detail-error-page">
      <GlassCard className="message-card detail-error-card"><strong>Չհաջողվեց բացել հերոսի էջը։</strong><span>Փորձիր կրկին։</span><button type="button" className="secondary-button" onClick={() => heroQuery.refetch()}>Կրկին փորձել</button></GlassCard>
    </div>
  )

  const paragraphs = biographyParagraphs(hero.bio)
  const birth = heroBirth(hero)
  const death = heroDeath(hero)

  return (
    <div className="hero-detail-page">
      <div className="detail-backdrop" aria-hidden="true">
        {hero.img_url ? <img src={hero.img_url} alt="" /> : null}<span />
      </div>
      <div className="hero-portrait-stage">
        {hero.img_url ? <img src={hero.img_url} alt={heroName(hero)} fetchPriority="high" /> : <div className="detail-placeholder">{initials(hero)}</div>}
        <div className="hero-portrait-stage__fade" />
      </div>

      <motion.article className="hero-story-sheet" initial={{ y: 28, opacity: .8 }} animate={{ y: 0, opacity: 1 }} transition={{ type: 'spring', stiffness: 260, damping: 28 }}>
        <div className="sheet-handle" />
        <div className="hero-title-block">
          <div className="detail-kicker"><Sparkles size={13} /> ՀԱՅՈՑ ՀԵՐՈՍՆԵՐ</div>
          <h1>{heroName(hero)}</h1>
          <p>{formatLife(hero)}</p>
        </div>

        <div className="hero-fact-deck">
          <div><span className="fact-icon"><CalendarDays size={18} /></span><small>Ծնվել է</small><strong>{birth || 'Տվյալ չկա'}</strong></div>
          <div><span className="fact-icon"><CalendarDays size={18} /></span><small>Զոհվել է</small><strong>{death || 'Տվյալ չկա'}</strong></div>
          <div><span className="fact-icon"><MapPin size={18} /></span><small>Մարզ</small><strong>{cleanText(hero.region) || 'Տվյալ չկա'}</strong></div>
          <div><span className="fact-icon"><Shield size={18} /></span><small>Մարտական ուղի</small><strong>{cleanText(hero.war) || 'Տվյալ չկա'}</strong></div>
        </div>

        <section className="story-section">
          <div className="story-section__head"><span>ԿԵՆՍԱԳՐՈՒԹՅՈՒՆ</span><h2>Նրա պատմությունը</h2></div>
          <div className="bio-timeline">
            {paragraphs.length ? paragraphs.map((paragraph, index) => (
              <motion.div className="bio-timeline__item" key={`${paragraph.slice(0, 30)}-${index}`} initial={{ opacity: 0, y: 8 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-40px' }}>
                <span className="bio-dot" />
                <p>{paragraph}</p>
              </motion.div>
            )) : <div className="bio-empty">Այս հերոսի կենսագրությունը դեռ լրացվում է։</div>}
          </div>
        </section>

        <div className="hero-detail-actions">
          <button type="button" className="primary-button" onClick={share}><Share2 size={17} /> Կիսվել պատմությամբ</button>
          {hero.bio_link ? <button type="button" className="secondary-button" onClick={() => tg.webApp?.openLink ? tg.webApp.openLink(hero.bio_link) : window.open(hero.bio_link, '_blank', 'noopener,noreferrer')}><ExternalLink size={17} /> Սկզբնաղբյուր</button> : null}
          {tg.capabilities.story && hero.img_url ? <button type="button" className="secondary-button" onClick={() => tg.shareToStory(hero.img_url, { text: `${heroName(hero)} — Հայոց Հերոսներ` })}><Sparkles size={17} /> Share to Story</button> : null}
        </div>
      </motion.article>
    </div>
  )
}
