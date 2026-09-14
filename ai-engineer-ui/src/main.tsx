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
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
