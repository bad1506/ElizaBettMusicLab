import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './glass-interactions.css'
import './SonaSferoomChat.css'
import './SonaCommercialFixes.css'
import './sona-cursor-glow.css'
import './SonaAbout.css'
import SonaPublic from './SonaPublic.tsx'
import SonaSferoomChat from './SonaSferoomChat.tsx'
import BillingPage from './BillingPage.tsx'

type TelegramWebApp = { ready?: () => void; expand?: () => void; setHeaderColor?: (color: string) => void; setBackgroundColor?: (color: string) => void; initData?: string; initDataUnsafe?: { user?: { id?: number; first_name?: string; last_name?: string; username?: string; photo_url?: string } } }
declare global { interface Window { Telegram?: { WebApp?: TelegramWebApp } } }
const telegram = window.Telegram?.WebApp
const initData = telegram?.initData?.trim() || ''
const api = import.meta.env.VITE_API_URL || '/api'
if (telegram) { telegram.ready?.(); telegram.expand?.(); telegram.setHeaderColor?.('#f5f5f3'); telegram.setBackgroundColor?.('#f5f5f3') }
const originalFetch = window.fetch.bind(window)
window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
  const path = (() => { try { return new URL(url, window.location.origin).pathname } catch { return url } })()
  const headers = new Headers(init?.headers || (input instanceof Request ? input.headers : undefined))
  const token = localStorage.getItem('sona_token')?.trim() || ''
  const isApiRequest = url.startsWith(api) || url.startsWith('/api/')
  // Only genuinely public endpoints bypass account authentication. Feature APIs such as
  // songwriter/trends consume paid/free quotas and must carry the account token (or Telegram auth).
  const isPublicRequest = path === '/api/auth/register' || path === '/api/auth/login' || path === '/api/auth/telegram' || path === '/api/public/yandex-chart' || path === '/api/health' || path === '/api/agents/skills'
  if (isApiRequest && !isPublicRequest) {
    if (token) headers.set('Authorization', `Bearer ${token}`)
    else if (initData) headers.set('X-Telegram-Init-Data', initData)
  }
  return originalFetch(input, { ...init, headers })
}
if (initData) {
  originalFetch(`${api}/auth/telegram`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ init_data: initData }) }).then(async r => r.ok ? r.json() : null).then(data => { if (data?.authenticated && data?.user) { sessionStorage.setItem('sona_telegram_user', JSON.stringify(data.user)); window.dispatchEvent(new CustomEvent('sona:telegram-auth', { detail: data.user })) } }).catch(() => undefined)
}
function CursorGlow() {
  useEffect(() => {
    let raf = 0
    const move = (event: PointerEvent) => {
      if (raf) cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        document.documentElement.style.setProperty('--sona-pointer-x', `${event.clientX}px`)
        document.documentElement.style.setProperty('--sona-pointer-y', `${event.clientY}px`)
        document.querySelectorAll<HTMLElement>('.sona-sferoom-panel,.sona-ai-card,.sona-surface-glow').forEach((panel) => {
          const rect = panel.getBoundingClientRect()
          panel.style.setProperty('--mx', `${event.clientX - rect.left}px`)
          panel.style.setProperty('--my', `${event.clientY - rect.top}px`)
        })
      })
    }
    window.addEventListener('pointermove', move, { passive: true })
    return () => { window.removeEventListener('pointermove', move); if (raf) cancelAnimationFrame(raf) }
  }, [])
  return null
}
function AppShell() {
  const isPricing = window.location.pathname.replace(/\/+$/, '') === '/pricing'
  return <><CursorGlow /><SonaPublic /><SonaSferoomChat />{isPricing && <BillingPage />}</>
}
createRoot(document.getElementById('root')!).render(<StrictMode><AppShell /></StrictMode>)
