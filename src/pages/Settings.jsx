import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BellRing, ChevronRight, Cloud, Expand, Gauge, Hand, Home, LockKeyhole, Moon, QrCode, ShieldCheck, Smartphone, Sun } from 'lucide-react'
import GlassCard from '../components/GlassCard.jsx'

function Toggle({ checked, onChange, disabled = false }) {
  return <button type="button" className={`ios-switch ${checked ? 'is-on' : ''}`} onClick={() => !disabled && onChange(!checked)} aria-pressed={checked} disabled={disabled}><span /></button>
}

function SettingsLink({ icon: Icon, title, subtitle, onClick }) {
  return <button type="button" className="settings-link-row" onClick={onClick}><span className="setting-icon"><Icon size={18} /></span><span className="settings-link-copy"><strong>{title}</strong>{subtitle ? <small>{subtitle}</small> : null}</span><ChevronRight size={17} /></button>
}

export default function Settings({ tg, settings, updateSettings }) {
  const navigate = useNavigate()
  const [homeStatus, setHomeStatus] = useState('')
  const resolvedAuto = tg.colorScheme === 'light' ? 'light' : 'dark'

  useEffect(() => { tg.setVerticalSwipesLocked(settings.lockVerticalSwipes) }, [settings.lockVerticalSwipes])
  useEffect(() => { tg.setClosingConfirmation(settings.closingConfirmation) }, [settings.closingConfirmation])

  const toggleFullscreen = (value) => {
    tg.haptic('medium')
    const changed = tg.setFullscreen(value)
    if (changed) updateSettings('fullscreen', value)
  }

  const themeOptions = [
    { id: 'auto', label: 'Auto', icon: Smartphone },
    { id: 'dark', label: 'Մուգ', icon: Moon },
    { id: 'light', label: 'Բաց', icon: Sun },
  ]

  const requestWrite = async () => {
    const ok = await tg.requestWriteAccess()
    tg.notify(ok ? 'success' : 'warning')
    await tg.showPopup({ title: ok ? 'Թույլատրված է' : 'Չթույլատրվեց', message: ok ? 'Բոտը կարող է քեզ հաղորդագրություններ ուղարկել Telegram-ի թույլատրած շրջանակում։' : 'Դու կարող ես դա փոխել Telegram-ի կարգավորումներում։', buttons: [{ type: 'ok' }] })
  }

  const addHome = async () => {
    tg.addToHomeScreen()
    const status = await tg.checkHomeScreen()
    setHomeStatus(status)
    tg.haptic('medium')
  }

  const scan = async () => {
    const value = await tg.scanQr('Սքանավորիր QR կոդը')
    if (value) tg.showPopup({ title: 'QR արդյունք', message: value.slice(0, 240), buttons: [{ type: 'ok' }] })
  }

  return (
    <div className="page settings-page">
      <header className="simple-header"><div><div className="eyebrow">ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ</div><h1>Կարգավորումներ</h1></div></header>

      <section className="settings-section">
        <div className="settings-section-title">Տեսք</div>
        <GlassCard className="settings-card settings-card--stacked">
          <div className="setting-row setting-row--vertical">
            <div className="setting-copy"><span className="setting-icon"><Moon size={18} /></span><div><strong>Թեմա</strong><small>Auto-ն հետևում է Telegram-ի թեմային ({resolvedAuto === 'dark' ? 'մուգ' : 'բաց'})</small></div></div>
            <div className="segmented-control">{themeOptions.map(({ id, label, icon: Icon }) => <button type="button" key={id} className={settings.theme === id ? 'is-active' : ''} onClick={() => { tg.haptic('light'); updateSettings('theme', id) }}><Icon size={14} />{label}</button>)}</div>
          </div>
          <div className="setting-row"><div className="setting-copy"><span className="setting-icon"><Gauge size={18} /></span><div><strong>Կոմպակտ քարտեր</strong><small>Ավելի շատ հերոսներ մեկ էկրանին</small></div></div><Toggle checked={settings.compactCards} onChange={(v) => updateSettings('compactCards', v)} /></div>
          <div className="setting-row"><div className="setting-copy"><span className="setting-icon"><Expand size={18} /></span><div><strong>Նվազեցնել շարժումները</strong><small>Հանգիստ page transition և shared-element animations</small></div></div><Toggle checked={settings.reducedMotion} onChange={(v) => updateSettings('reducedMotion', v)} /></div>
        </GlassCard>
      </section>

      <section className="settings-section">
        <div className="settings-section-title">Հավելված</div>
        <GlassCard className="settings-card settings-card--stacked">
          <div className="setting-row"><div className="setting-copy"><span className="setting-icon"><Expand size={18} /></span><div><strong>Լիաէկրան ռեժիմ</strong><small>{!tg.isTelegram ? 'Հասանելի է Telegram-ում' : tg.fullscreenSupported ? 'Օգտագործել ամբողջ հասանելի էկրանը' : 'Քո Telegram-ը չի աջակցում fullscreen API-ին'}</small></div></div><Toggle checked={settings.fullscreen || tg.isFullscreen} onChange={toggleFullscreen} disabled={!tg.isTelegram || !tg.fullscreenSupported} /></div>
          <div className="setting-row"><div className="setting-copy"><span className="setting-icon"><Hand size={18} /></span><div><strong>Haptic feedback</strong><small>Native թեթև vibration գործողությունների ժամանակ</small></div></div><Toggle checked={settings.haptics} onChange={(v) => updateSettings('haptics', v)} /></div>
          <div className="setting-row"><div className="setting-copy"><span className="setting-icon"><Smartphone size={18} /></span><div><strong>Արգելել vertical swipe-ը</strong><small>Նվազեցնում է պատահական փակվելը</small></div></div><Toggle checked={settings.lockVerticalSwipes} onChange={(v) => { updateSettings('lockVerticalSwipes', v); tg.setVerticalSwipesLocked(v) }} disabled={!tg.isTelegram || !tg.capabilities.verticalSwipes} /></div>
          <div className="setting-row"><div className="setting-copy"><span className="setting-icon"><LockKeyhole size={18} /></span><div><strong>Փակման հաստատում</strong><small>Telegram-ը հարցնում է՝ փակե՞լ Mini App-ը</small></div></div><Toggle checked={settings.closingConfirmation} onChange={(v) => updateSettings('closingConfirmation', v)} disabled={!tg.isTelegram || !tg.capabilities.closingConfirmation} /></div>
          <div className="setting-row"><div className="setting-copy"><span className="setting-icon"><Cloud size={18} /></span><div><strong>Sync Telegram Cloud-ում</strong><small>Կարգավորումները համաժամեցնել Telegram CloudStorage-ով</small></div></div><Toggle checked={settings.syncTelegramCloud} onChange={(v) => updateSettings('syncTelegramCloud', v)} disabled={!tg.isTelegram || !tg.capabilities.cloudStorage} /></div>
        </GlassCard>
      </section>

      {/* <section className="settings-section">
        <div className="settings-section-title">Գործիքներ</div>
        <GlassCard className="settings-card settings-card--links">
          <SettingsLink icon={BellRing} title="Թույլատրել բոտի հաղորդագրությունները" subtitle="Telegram requestWriteAccess" onClick={requestWrite} />
          <SettingsLink icon={Home} title="Ավելացնել Home Screen" subtitle={homeStatus ? `Status: ${homeStatus}` : 'Telegram shortcut, եթե աջակցվում է'} onClick={addHome} />
        </GlassCard>
      </section> */}


      <section className="settings-section">
        <div className="settings-section-title">Իրավական և կառավարում</div>
        <GlassCard className="settings-card settings-card--links">
          <SettingsLink icon={ShieldCheck} title="Privacy Policy" onClick={() => navigate('/privacy')} />
          <SettingsLink icon={ShieldCheck} title="Terms of Use" onClick={() => navigate('/terms')} />
        </GlassCard>
      </section>

    </div>
  )
}
