import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Telegram WebApp is optional in a normal browser, but must be initialized
// before the React UI starts when the app is opened inside Telegram.
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
if (telegram) {
  telegram.ready?.()
  telegram.expand?.()
  telegram.setHeaderColor?.('#f5f5f3')
  telegram.setBackgroundColor?.('#f5f5f3')

  // initData is sent to the backend for cryptographic validation.
  // initDataUnsafe is only used as an immediate UI hint and is never trusted server-side.
  const initData = telegram.initData?.trim()
  if (initData) {
    const api = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
    fetch(`${api}/auth/telegram`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: initData }),
    })
      .then(async (response) => {
        if (!response.ok) return null
        return response.json()
      })
      .then((data) => {
        if (data?.authenticated && data?.user) {
          sessionStorage.setItem('eliza_telegram_user', JSON.stringify(data.user))
          window.dispatchEvent(new CustomEvent('eliza:telegram-auth', { detail: data.user }))
        }
      })
      .catch(() => {
        // Authentication is retried on the next Mini App launch.
      })
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
