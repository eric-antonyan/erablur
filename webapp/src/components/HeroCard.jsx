import { MapPin, Shield } from 'lucide-react'
import { motion } from 'framer-motion'
import { formatLife, heroName, initials } from '../lib.js'

export default function HeroCard({ hero, onClick, featured = false, onPrefetch }) {
  return (
    <motion.button
      type="button"
      className={`hero-card ${featured ? 'hero-card--featured' : ''}`}
      onClick={onClick}
      onPointerEnter={onPrefetch}
      onTouchStart={onPrefetch}
      whileTap={{ scale: 0.985 }}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 320, damping: 30 }}
    >
      <div className="hero-card__media">
        {hero?.img_url ? <img src={hero.img_url} alt={heroName(hero)} loading={featured ? 'eager' : 'lazy'} decoding="async" /> : <span>{initials(hero)}</span>}
        <div className="hero-card__media-shade" />
      </div>
      <div className="hero-card__body">
        <div className="hero-card__name">{heroName(hero)}</div>
        <div className="hero-card__life">{formatLife(hero)}</div>
        <div className="hero-card__meta">
          {hero?.war ? <span><Shield size={13} />{hero.war}</span> : null}
          {hero?.region ? <span><MapPin size={13} />{hero.region}</span> : null}
        </div>
      </div>
    </motion.button>
  )
}
