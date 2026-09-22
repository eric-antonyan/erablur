import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { Clock3, RefreshCw, ShieldBan } from 'lucide-react'
import { Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { api } from './api.js'
import TabBar from './components/TabBar.jsx'
import { useAppSettings } from './hooks/useAppSettings.js'
import { useTelegram } from './hooks/useTelegram.js'
import AdminPanel from './pages/AdminPanel.jsx'
import EventDetail from './pages/EventDetail.jsx'
import Events from './pages/Events.jsx'
import HeroDetail from './pages/HeroDetail.jsx'
import Home from './pages/Home.jsx'
import Museum from './pages/Museum.jsx'
import Privacy from './pages/Privacy.jsx'
import Profile from './pages/Profile.jsx'
import Settings from './pages/Settings.jsx'
import Terms from './pages/Terms.jsx'
import { createRealtimeClient } from './realtime.js'

const DETAIL_ROUTES = ['/hero/', '/event/']

function ModerationScreen({ moderation, tg }) {
  const blocked = moderation?.status === 'blocked'
  const until = moderation?.restricted_until ? new Date(moderation.restricted_until) : null
  const untilText = until && Number.isFinite(until.getTime())
    ? new Intl.DateTimeFormat('hy-AM', { dateStyle: 'long', timeStyle: 'short' }).format(until)
    : ''

  return (
    <div className="ios26-access-screen">
      <div className="ios26-access-ambient ios26-access-ambient--one" />
      <div className="ios26-access-ambient ios26-access-ambient--two" />
      <section className={`ios26-access-sheet ${blocked ? 'is-blocked' : 'is-restricted'}`}>
        <div className="ios26-access-symbol-wrap">
          <div className="ios26-access-symbol-ring" />
          <div className="ios26-access-symbol">{blocked ? <ShieldBan size={34} /> : <Clock3 size={34} />}</div>
        </div>
        <span className="ios26-access-kicker">ՀԱՅՈՑ ՀԵՐՈՍՆԵՐ</span>
        <h1>{blocked ? 'Մուտքը սահմանափակված է' : 'Ժամանակավոր սահմանափակում'}</h1>
        <p className="ios26-access-lead">{blocked
          ? 'Այս Telegram հաշվի համար Mini App-ի հասանելիությունը դադարեցված է։'
          : 'Այս Telegram հաշվի Mini App հասանելիությունը ժամանակավորապես սահմանափակված է։'}</p>

        <div className="ios26-access-detail-card">
          <div><span>Կարգավիճակ</span><strong>{blocked ? 'Blocked' : 'Restricted'}</strong></div>
          {!blocked && untilText ? <div><span>Ավարտվում է</span><strong>{untilText}</strong></div> : null}
          {moderation?.reason ? <div className="is-reason"><span>Պատճառ</span><strong>{moderation.reason}</strong></div> : null}
        </div>

        <div className="ios26-access-actions">
          <button type="button" className="ios26-access-primary" onClick={() => window.location.reload()}><RefreshCw size={17} /> Ստուգել կրկին</button>
          {tg?.webApp?.close ? <button type="button" className="ios26-access-secondary" onClick={() => tg.webApp.close()}>Փակել Mini App-ը</button> : null}
        </div>
        <p className="ios26-access-footnote">Եթե կարծում եք, որ սահմանափակումը սխալ է, կապվեք bot-ի ադմինիստրատորի հետ։</p>
      </section>
    </div>
  )
}

function TelegramAccessLoading() {
  return (
    <div className="access-loading">
      <div className="access-loading__spinner" />
      <span>Բացվում է Հայոց Հերոսներ…</span>
    </div>
  )
}

export default function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { settings, update, replace } = useAppSettings()
  const tg = useTelegram({ hapticsEnabled: settings.haptics })
  const syncedRef = useRef(false)
  const realtimeRef = useRef(null)
  const [liveModeration, setLiveModeration] = useState(null)

  const isAdmin = location.pathname.startsWith('/admin')
  const access = useQuery({
    queryKey: ['telegram-access'],
    queryFn: api.me,
    enabled: tg.isTelegram && !isAdmin,
    staleTime: 30_000,
    retry: 1,
    meta: { persist: false },
  })

  useEffect(() => {
    if (!tg.isTelegram || isAdmin || !tg.webApp?.initData) return
    const client = createRealtimeClient()
    realtimeRef.current = client
    const unsubscribe = client.subscribe((message) => {
      if (message?.type === 'moderation:update' && message?.moderation) setLiveModeration(message.moderation)
      if (message?.type === 'events:changed') {
        queryClient.invalidateQueries({ queryKey: ['events'] })
        queryClient.invalidateQueries({ queryKey: ['event'] })
      }
    })
    client.connect({ type: 'auth', role: 'user', initData: tg.webApp.initData })
    return () => {
      unsubscribe()
      client.close()
      if (realtimeRef.current === client) realtimeRef.current = null
    }
  }, [tg.isTelegram, tg.webApp, isAdmin, queryClient])

  useEffect(() => {
    if (access.data?.moderation) setLiveModeration(access.data.moderation)
  }, [access.data?.moderation])

  useEffect(() => {
    if (liveModeration?.status !== 'restricted' || !liveModeration?.restricted_until) return
    const until = Date.parse(liveModeration.restricted_until)
    if (!Number.isFinite(until)) return
    const delay = Math.max(0, until - Date.now())
    const timer = setTimeout(() => {
      setLiveModeration((current) => current?.status === 'restricted' ? { ...current, status: 'active', reason: '', restricted_until: '' } : current)
      access.refetch()
    }, Math.min(delay + 500, 2_147_000_000))
    return () => clearTimeout(timer)
  }, [liveModeration?.status, liveModeration?.restricted_until])

  const resolvedTheme = settings.theme === 'auto'
    ? (tg.colorScheme === 'light' ? 'light' : 'dark')
    : settings.theme

  const isDetail = DETAIL_ROUTES.some((prefix) => location.pathname.startsWith(prefix))
  const isUtility = ['/terms', '/privacy', '/admin'].some((path) => location.pathname.startsWith(path))
  const showTabBar = !isDetail && !isUtility

  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme
    document.documentElement.style.colorScheme = resolvedTheme
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', resolvedTheme === 'light' ? '#f4f5f8' : '#080a0f')
    tg.setChromeTheme(resolvedTheme)
  }, [resolvedTheme, tg.setChromeTheme])

  useEffect(() => {
    if (!tg.isTelegram) return
    if (settings.fullscreen) tg.setFullscreen(true)
    tg.setVerticalSwipesLocked(settings.lockVerticalSwipes)
    tg.setClosingConfirmation(settings.closingConfirmation)
  }, [tg.isTelegram, settings.fullscreen, settings.lockVerticalSwipes, settings.closingConfirmation])

  useEffect(() => {
    if (!tg.isTelegram || !tg.capabilities.cloudStorage || syncedRef.current) return
    syncedRef.current = true
    tg.cloudGet('hh_settings_v3').then((value) => {
      if (!value) return
      try { replace(JSON.parse(value)) } catch {}
    })
  }, [tg.isTelegram, tg.capabilities.cloudStorage])

  useEffect(() => {
    if (!tg.isTelegram || !settings.syncTelegramCloud || !tg.capabilities.cloudStorage || !syncedRef.current) return
    const timer = setTimeout(() => tg.cloudSet('hh_settings_v3', JSON.stringify(settings)), 350)
    return () => clearTimeout(timer)
  }, [settings, tg.isTelegram, tg.capabilities.cloudStorage])

  useEffect(() => {
    const app = tg.webApp
    if (!app) return
    try {
      app.MainButton?.hide?.()
      app.MainButton?.setParams?.({ is_visible: false, is_active: false })
      app.SecondaryButton?.hide?.()
      app.SecondaryButton?.setParams?.({ is_visible: false, is_active: false })
    } catch {}

    const onSettings = () => navigate('/settings')
    try {
      app.SettingsButton?.show?.()
      app.SettingsButton?.onClick?.(onSettings)
    } catch {}
    return () => { try { app.SettingsButton?.offClick?.(onSettings) } catch {} }
  }, [location.pathname, tg.webApp, navigate])

  useEffect(() => {
    const app = tg.webApp
    const backButton = app?.BackButton
    if (!tg.isTelegram || !backButton || isAdmin) return

    const nativeBackRoutes =
      location.pathname.startsWith('/hero/') ||
      location.pathname.startsWith('/event/') ||
      location.pathname === '/terms' ||
      location.pathname === '/privacy'

    const onNativeBack = () => {
      tg.haptic('light')
      // Telegram detail pages can also be opened directly from a deep link.
      // In that case there may be no useful app history entry, so return home.
      if (window.history.length > 1) navigate(-1)
      else navigate('/', { replace: true })
    }

    try {
      backButton.offClick?.(onNativeBack)
      if (nativeBackRoutes) {
        backButton.show?.()
        backButton.onClick?.(onNativeBack)
      } else {
        backButton.hide?.()
      }
    } catch {}

    return () => {
      try { backButton.offClick?.(onNativeBack) } catch {}
    }
  }, [tg.isTelegram, tg.webApp, tg.haptic, isAdmin, location.pathname, navigate])

  const motionProps = useMemo(() => settings.reducedMotion
    ? { initial: false, animate: { opacity: 1 }, exit: { opacity: 1 }, transition: { duration: 0 } }
    : {
        initial: { opacity: 0, y: 12, filter: 'blur(5px)' },
        animate: { opacity: 1, y: 0, filter: 'blur(0px)' },
        exit: { opacity: 0, y: -8, filter: 'blur(3px)' },
        transition: { duration: 0.28, ease: [0.22, 1, 0.36, 1] },
      }, [settings.reducedMotion])

  const moderation = liveModeration || access.data?.moderation
  const restricted = moderation?.status === 'blocked' || moderation?.status === 'restricted'

  if (tg.isTelegram && !isAdmin && access.isLoading && !moderation) return <TelegramAccessLoading />
  if (tg.isTelegram && !isAdmin && restricted) return <ModerationScreen moderation={moderation} tg={tg} />

  return (
    <div className="app-shell" style={{ '--tg-viewport-height': `${tg.viewportHeight}px` }}>
      <div className="ambient ambient--one" />
      <div className="ambient ambient--two" />
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.main key={location.pathname} className="route-shell" {...motionProps}>
          <Routes location={location}>
            <Route path="/" element={<Home tg={tg} />} />
            <Route path="/museum" element={<Museum tg={tg} />} />
            <Route path="/events" element={<Events tg={tg} />} />
            <Route path="/profile" element={<Profile tg={tg} />} />
            <Route path="/settings" element={<Settings tg={tg} settings={settings} updateSettings={update} />} />
            <Route path="/hero/:id" element={<HeroDetail tg={tg} />} />
            <Route path="/event/:id" element={<EventDetail tg={tg} />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/admin" element={<AdminPanel />} />
            <Route path="*" element={<Home tg={tg} />} />
          </Routes>
        </motion.main>
      </AnimatePresence>
      {showTabBar ? <TabBar haptic={tg.haptic} /> : null}
    </div>
  )
}
