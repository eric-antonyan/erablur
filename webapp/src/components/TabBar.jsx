import { CalendarDays, House, Search, Settings, UserRound } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

const items = [
  { path: '/', label: 'Գլխավոր', icon: House },
  { path: '/museum', label: 'Թանգարան', icon: Search },
  { path: '/events', label: 'Օրացույց', icon: CalendarDays },
  { path: '/profile', label: 'Իմ էջը', icon: UserRound },
  { path: '/settings', label: 'Կարգ.', icon: Settings },
]

export default function TabBar({ haptic }) {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <nav className="tabbar-wrap" aria-label="Գլխավոր նավիգացիա">
      <div className="tabbar liquid-pill">
        {items.map(({ path, label, icon: Icon }) => {
          const active = path === '/' ? location.pathname === '/' : location.pathname.startsWith(path)
          return (
            <button
              type="button"
              key={path}
              className={`tabbar__item ${active ? 'is-active' : ''}`}
              onClick={() => {
                haptic?.('light')
                navigate(path)
              }}
            >
              {active ? <span className="tabbar__active" /> : null}
              <Icon size={20} strokeWidth={active ? 2.4 : 2} />
              <span>{label}</span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
