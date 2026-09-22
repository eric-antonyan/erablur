import { useCallback, useEffect, useMemo, useState } from 'react'

export function useTelegram({ hapticsEnabled = true } = {}) {
  const webApp = useMemo(() => window.Telegram?.WebApp || null, [])
  const [isFullscreen, setIsFullscreen] = useState(Boolean(webApp?.isFullscreen))
  const systemScheme = typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
  const [colorScheme, setColorScheme] = useState(webApp?.colorScheme || systemScheme)
  const [viewportHeight, setViewportHeight] = useState(webApp?.viewportStableHeight || window.innerHeight)

  useEffect(() => {
    if (!webApp) return
    const root = document.documentElement
    root.dataset.tgPlatform = String(webApp.platform || 'web').toLowerCase()
    try { webApp.ready(); webApp.expand() } catch {}

    const applyInsets = () => {
      const safe = webApp.safeAreaInset || {}
      const content = webApp.contentSafeAreaInset || {}
      for (const key of ['top', 'right', 'bottom', 'left']) {
        root.style.setProperty(`--tg-safe-area-inset-${key}`, `${Number(safe[key]) || 0}px`)
        root.style.setProperty(`--tg-content-safe-area-inset-${key}`, `${Number(content[key]) || 0}px`)
      }
    }
    const fullscreenChanged = () => setIsFullscreen(Boolean(webApp.isFullscreen))
    const themeChanged = () => setColorScheme(webApp.colorScheme || systemScheme)
    const viewportChanged = () => {
      const value = webApp.viewportStableHeight || webApp.viewportHeight || window.innerHeight
      setViewportHeight(value)
      document.documentElement.style.setProperty('--tg-viewport-stable-height', `${value}px`)
    }
    const safeAreaChanged = () => applyInsets()
    const contentSafeAreaChanged = () => applyInsets()

    applyInsets()
    viewportChanged()
    try {
      webApp.onEvent?.('fullscreenChanged', fullscreenChanged)
      webApp.onEvent?.('themeChanged', themeChanged)
      webApp.onEvent?.('viewportChanged', viewportChanged)
      webApp.onEvent?.('safeAreaChanged', safeAreaChanged)
      webApp.onEvent?.('contentSafeAreaChanged', contentSafeAreaChanged)
    } catch {}

    return () => {
      try {
        webApp.offEvent?.('fullscreenChanged', fullscreenChanged)
        webApp.offEvent?.('themeChanged', themeChanged)
        webApp.offEvent?.('viewportChanged', viewportChanged)
        webApp.offEvent?.('safeAreaChanged', safeAreaChanged)
        webApp.offEvent?.('contentSafeAreaChanged', contentSafeAreaChanged)
      } catch {}
      if (root.dataset.tgPlatform === String(webApp.platform || 'web').toLowerCase()) {
        delete root.dataset.tgPlatform
      }
    }
  }, [webApp])

  const user = webApp?.initDataUnsafe?.user || null
  const isTelegram = Boolean(webApp?.initData)

  const haptic = useCallback((type = 'light') => {
    if (!hapticsEnabled) return
    try { webApp?.HapticFeedback?.impactOccurred(type) } catch {}
  }, [webApp, hapticsEnabled])

  const notify = useCallback((type = 'success') => {
    if (!hapticsEnabled) return
    try { webApp?.HapticFeedback?.notificationOccurred(type) } catch {}
  }, [webApp, hapticsEnabled])

  const selection = useCallback(() => {
    if (!hapticsEnabled) return
    try { webApp?.HapticFeedback?.selectionChanged() } catch {}
  }, [webApp, hapticsEnabled])

  const setFullscreen = useCallback((enabled) => {
    if (!webApp) return false
    try {
      if (enabled) {
        if (typeof webApp.requestFullscreen !== 'function') return false
        webApp.requestFullscreen()
      } else {
        if (typeof webApp.exitFullscreen !== 'function') return false
        webApp.exitFullscreen()
      }
      return true
    } catch { return false }
  }, [webApp])

  const setVerticalSwipesLocked = useCallback((locked) => {
    if (!webApp) return false
    try {
      if (locked && typeof webApp.disableVerticalSwipes === 'function') webApp.disableVerticalSwipes()
      if (!locked && typeof webApp.enableVerticalSwipes === 'function') webApp.enableVerticalSwipes()
      return true
    } catch { return false }
  }, [webApp])

  const setClosingConfirmation = useCallback((enabled) => {
    if (!webApp) return false
    try {
      if (enabled) webApp.enableClosingConfirmation?.()
      else webApp.disableClosingConfirmation?.()
      return true
    } catch { return false }
  }, [webApp])

  const setChromeTheme = useCallback((mode) => {
    if (!webApp) return
    const dark = mode !== 'light'
    const background = dark ? '#080a0f' : '#f4f5f8'
    try {
      webApp.setHeaderColor?.(background)
      webApp.setBackgroundColor?.(background)
    } catch {}
  }, [webApp])

  const share = useCallback((url, text = '') => {
    const telegramShare = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`
    try {
      if (webApp?.openTelegramLink) return webApp.openTelegramLink(telegramShare)
    } catch {}
    if (navigator.share) return navigator.share({ title: text, text, url })
    return navigator.clipboard?.writeText(url)
  }, [webApp])

  const cloudGet = useCallback((key) => new Promise((resolve) => {
    if (!webApp?.CloudStorage?.getItem) return resolve(null)
    try { webApp.CloudStorage.getItem(key, (error, value) => resolve(error ? null : value || null)) }
    catch { resolve(null) }
  }), [webApp])

  const cloudSet = useCallback((key, value) => new Promise((resolve) => {
    if (!webApp?.CloudStorage?.setItem) return resolve(false)
    try { webApp.CloudStorage.setItem(key, String(value), (error) => resolve(!error)) }
    catch { resolve(false) }
  }), [webApp])

  const showPopup = useCallback((params) => new Promise((resolve) => {
    if (!webApp?.showPopup) return resolve(null)
    try { webApp.showPopup(params, (id) => resolve(id || null)) }
    catch { resolve(null) }
  }), [webApp])

  const requestWriteAccess = useCallback(() => new Promise((resolve) => {
    if (!webApp?.requestWriteAccess) return resolve(false)
    try { webApp.requestWriteAccess((allowed) => resolve(Boolean(allowed))) }
    catch { resolve(false) }
  }), [webApp])

  const scanQr = useCallback((text = 'Սքանավորել QR կոդը') => new Promise((resolve) => {
    if (!webApp?.showScanQrPopup) return resolve(null)
    try {
      webApp.showScanQrPopup({ text }, (value) => {
        if (value) {
          webApp.closeScanQrPopup?.()
          resolve(value)
          return true
        }
        return false
      })
    } catch { resolve(null) }
  }), [webApp])

  const addToHomeScreen = useCallback(() => {
    try { webApp?.addToHomeScreen?.(); return true } catch { return false }
  }, [webApp])

  const checkHomeScreen = useCallback(() => new Promise((resolve) => {
    if (!webApp?.checkHomeScreenStatus) return resolve('unsupported')
    try { webApp.checkHomeScreenStatus((status) => resolve(status || 'unknown')) }
    catch { resolve('unknown') }
  }), [webApp])

  const shareToStory = useCallback((mediaUrl, params = {}) => {
    try {
      if (!webApp?.shareToStory) return false
      webApp.shareToStory(mediaUrl, params)
      return true
    } catch { return false }
  }, [webApp])

  const capabilities = useMemo(() => ({
    fullscreen: Boolean(webApp?.requestFullscreen && webApp?.exitFullscreen),
    verticalSwipes: Boolean(webApp?.disableVerticalSwipes && webApp?.enableVerticalSwipes),
    closingConfirmation: Boolean(webApp?.enableClosingConfirmation),
    cloudStorage: Boolean(webApp?.CloudStorage),
    qrScanner: Boolean(webApp?.showScanQrPopup),
    writeAccess: Boolean(webApp?.requestWriteAccess),
    homeScreen: Boolean(webApp?.addToHomeScreen),
    story: Boolean(webApp?.shareToStory),
    settingsButton: Boolean(webApp?.SettingsButton),
    mainButton: Boolean(webApp?.MainButton),
    secondaryButton: Boolean(webApp?.SecondaryButton),
    haptics: Boolean(webApp?.HapticFeedback),
    popup: Boolean(webApp?.showPopup),
    safeArea: Boolean(webApp?.safeAreaInset || webApp?.contentSafeAreaInset),
    downloadFile: Boolean(webApp?.downloadFile),
    switchInlineQuery: Boolean(webApp?.switchInlineQuery),
    emojiStatus: Boolean(webApp?.requestEmojiStatusAccess),
  }), [webApp])

  return {
    webApp, user, isTelegram, haptic, notify, selection,
    platform: webApp?.platform || 'web', version: webApp?.version || '',
    isFullscreen, fullscreenSupported: capabilities.fullscreen,
    colorScheme, viewportHeight, capabilities,
    setFullscreen, setVerticalSwipesLocked, setClosingConfirmation, setChromeTheme,
    share, cloudGet, cloudSet, showPopup, requestWriteAccess, scanQr,
    addToHomeScreen, checkHomeScreen, shareToStory,
  }
}
