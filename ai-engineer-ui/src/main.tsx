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

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
