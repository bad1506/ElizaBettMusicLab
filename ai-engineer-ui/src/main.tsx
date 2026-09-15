import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

type TelegramWebApp = {
  ready?: () => void
  expand?: () => void
  setHeaderColor?: (color: string) => void
  setBackgroundColor?: (color: string) => void
  initData?: string
  initDataUnsafe?: { user?: { id?: number; first_name?: string; last_name?: string; username?: string; photo_url?: string } }
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp }
  }
}

const telegram = window.Telegram?.WebApp
const initData = telegram?.initData?.trim() || ''
const api = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://127.0.0.1:8000' : 'https://elizabettmusiclab-1.onrender.com')

if (telegram) {
  telegram.ready?.()
  telegram.expand?.()
  telegram.setHeaderColor?.('#f5f5f3')
  telegram.setBackgroundColor?.('#f5f5f3')
}

// Attach the signed Telegram Mini App payload to every backend request.
// The backend validates it cryptographically; initDataUnsafe is never trusted.
if (initData) {
  const originalFetch = window.fetch.bind(window)
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
    if (!url.startsWith(api) || url.endsWith('/auth/telegram')) return originalFetch(input, init)
    const headers = new Headers(init?.headers || (input instanceof Request ? input.headers : undefined))
    headers.set('X-Telegram-Init-Data', initData)
    return originalFetch(input, { ...init, headers })
  }

  originalFetch(`${api}/auth/telegram`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ init_data: initData }),
  })
    .then(async (response) => response.ok ? response.json() : null)
    .then((data) => {
      if (data?.authenticated && data?.user) {
        sessionStorage.setItem('eliza_telegram_user', JSON.stringify(data.user))
        window.dispatchEvent(new CustomEvent('eliza:telegram-auth', { detail: data.user }))
      }
    })
    .catch(() => undefined)
}

// Keep the existing single-page UI shareable with real URLs.
// The App component owns the visible page state; this bridge synchronizes it
// with browser history without adding a router dependency to the Mini App.
const ROUTES: Record<string, string> = {
  '/': 'home',
  '/tools': 'tools',
  '/tracks': 'tracks',
  '/projects': 'projects',
  '/pricing': 'pricing',
  '/about': 'about',
}
const PAGE_BY_LABEL: Record<string, string> = {
  'Главная': '/', 'AI Инструменты': '/tools', 'Треки': '/tracks', 'Проекты': '/projects', 'Тарифы': '/pricing', 'О нас': '/about',
  'Home': '/', 'AI Tools': '/tools', 'Tracks': '/tracks', 'Projects': '/projects', 'Pricing': '/pricing', 'About': '/about',
}

function syncPageFromUrl() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/'
  const page = ROUTES[path] || 'home'
  const buttons = Array.from(document.querySelectorAll('button'))
  const labels = Object.entries(ROUTES).find(([, value]) => value === page)?.[0]
  const labelMap = labels === '/' ? ['Главная', 'Home'] : Object.entries(PAGE_BY_LABEL).filter(([, route]) => route === path).map(([label]) => label)
  const button = buttons.find((candidate) => labelMap.includes(candidate.textContent?.trim() || ''))
  button?.click()
  document.title = page === 'home' ? 'Eliza Bett Music Lab' : `${page === 'tools' ? 'AI Music Tools' : page[0].toUpperCase() + page.slice(1)} · Eliza Bett Music Lab`
}

window.addEventListener('popstate', syncPageFromUrl)
window.addEventListener('click', (event) => {
  const target = event.target as HTMLElement | null
  const button = target?.closest('button')
  const label = button?.textContent?.trim() || ''
  const route = PAGE_BY_LABEL[label]
  if (!route || route === window.location.pathname) return
  window.history.pushState({}, '', route)
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

requestAnimationFrame(() => syncPageFromUrl())
