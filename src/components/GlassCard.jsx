import { motion } from 'framer-motion'

export default function GlassCard({ children, className = '', onClick, ...props }) {
  const interactive = Boolean(onClick)
  return (
    <motion.div
      className={`glass-card ${interactive ? 'glass-card--interactive' : ''} ${className}`}
      onClick={onClick}
      whileTap={interactive ? { scale: 0.985 } : undefined}
      {...props}
    >
      {children}
    </motion.div>
  )
}
