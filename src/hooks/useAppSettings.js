import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'hayoc-heros:settings:v3'

export const DEFAULT_SETTINGS = {
  theme: 'auto',
  fullscreen: false,
  haptics: true,
  reducedMotion: false,
  compactCards: false,
  lockVerticalSwipes: true,
  closingConfirmation: false,
  syncTelegramCloud: true,
}

function readSettings() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
    return { ...DEFAULT_SETTINGS, ...stored }
  } catch { return { ...DEFAULT_SETTINGS } }
}

export function useAppSettings() {
  const [settings, setSettings] = useState(readSettings)
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(settings)) } catch {}
    document.documentElement.dataset.reducedMotion = settings.reducedMotion ? 'true' : 'false'
    document.documentElement.dataset.compactCards = settings.compactCards ? 'true' : 'false'
  }, [settings])

  const update = useCallback((key, value) => setSettings((current) => ({ ...current, [key]: value })), [])
  const replace = useCallback((value) => setSettings({ ...DEFAULT_SETTINGS, ...value }), [])
  const reset = useCallback(() => setSettings({ ...DEFAULT_SETTINGS }), [])
  return { settings, update, replace, reset }
}
