export function LoadingCards({ count = 6 }) {
  return <div className="hero-grid">{Array.from({ length: count }, (_, i) => <div className="skeleton hero-card-skeleton" key={i} />)}</div>
}

export function PageLoader() {
  return <div className="page-loader"><span className="spinner" /><div>Բեռնվում է…</div></div>
}
