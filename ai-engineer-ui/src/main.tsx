import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './glass-interactions.css'
import App from './App.tsx'

type TelegramWebApp = { ready?: () => void; expand?: () => void; setHeaderColor?: (color: string) => void; setBackgroundColor?: (color: string) => void; initData?: string; initDataUnsafe?: { user?: { id?: number; first_name?: string; last_name?: string; username?: string; photo_url?: string } } }
declare global { interface Window { Telegram?: { WebApp?: TelegramWebApp } } }
const telegram = window.Telegram?.WebApp
const initData = telegram?.initData?.trim() || ''
const api = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://127.0.0.1:8000' : 'https://elizabettmusiclab-1.onrender.com')
if (telegram) { telegram.ready?.(); telegram.expand?.(); telegram.setHeaderColor?.('#f5f5f3'); telegram.setBackgroundColor?.('#f5f5f3') }
if (initData) {
  const originalFetch = window.fetch.bind(window)
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => { const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url; if (!url.startsWith(api) || url.endsWith('/auth/telegram')) return originalFetch(input, init); const headers = new Headers(init?.headers || (input instanceof Request ? input.headers : undefined)); headers.set('X-Telegram-Init-Data', initData); return originalFetch(input, { ...init, headers }) }
  originalFetch(`${api}/auth/telegram`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ init_data: initData }) }).then(async r => r.ok ? r.json() : null).then(data => { if (data?.authenticated && data?.user) { sessionStorage.setItem('sova_telegram_user', JSON.stringify(data.user)); window.dispatchEvent(new CustomEvent('sova:telegram-auth', { detail: data.user })) } }).catch(() => undefined)
}
const ROUTES: Record<string, string> = { '/': 'home', '/tools': 'tools', '/tracks': 'tracks', '/projects': 'projects', '/pricing': 'pricing', '/about': 'about' }
const PAGE_BY_LABEL: Record<string, string> = { 'Главная': '/', 'AI Инструменты': '/tools', 'Треки': '/tracks', 'Проекты': '/projects', 'Тарифы': '/pricing', 'О нас': '/about', Home: '/', 'AI Tools': '/tools', Tracks: '/tracks', Projects: '/projects', Pricing: '/pricing', About: '/about' }
function syncPageFromUrl() { const path = window.location.pathname.replace(/\/+$/, '') || '/'; const page = ROUTES[path] || 'home'; const labels = Object.entries(PAGE_BY_LABEL).filter(([, route]) => route === path).map(([label]) => label); const button = Array.from(document.querySelectorAll('button')).find(candidate => labels.includes(candidate.textContent?.trim() || '')); button?.click(); document.title = page === 'home' ? 'SØNA — Music Intelligence' : `${page === 'tools' ? 'AI Music Tools' : page[0].toUpperCase() + page.slice(1)} · SØNA` }
window.addEventListener('popstate', syncPageFromUrl)
window.addEventListener('click', event => { const button = (event.target as HTMLElement | null)?.closest('button'); const route = PAGE_BY_LABEL[button?.textContent?.trim() || '']; if (!route || route === window.location.pathname) return; window.history.pushState({}, '', route) })
createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
requestAnimationFrame(() => syncPageFromUrl())
