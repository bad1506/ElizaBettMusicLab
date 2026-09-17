import { useEffect, useState } from "react";
import { ArrowRight, Check, RefreshCw } from "lucide-react";
import "./BillingPage.css";

const API = import.meta.env.VITE_API_URL || "/api";
type Feature = { limit?: number };
type Plan = { key: string; name?: string; price_rub?: number; features?: Record<string, Feature>; storage_mb?: number };
type Usage = { plan?: string; plan_name?: string; subscription_status?: string; period_end?: string | null; features?: Record<string, { used?: number; limit?: number; remaining?: number }> };

async function api(path: string, init?: RequestInit) {
  const headers = new Headers(init?.headers || {});
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = localStorage.getItem("sona_token");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API}${path}`, { ...init, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
  return data;
}
function rub(value = 0) { return new Intl.NumberFormat("ru-RU").format(value) + " ₽"; }
function prettyFeature(key: string) { return ({ chat: "SØNA Chat", songwriter: "AI Songwriter", analysis: "Audio Analysis", mastering: "AI Mastering", trends: "Trends", production: "Production", stems: "Stem Separation" } as Record<string, string>)[key] || key; }

export default function BillingPage() {
  const [plans, setPlans] = useState<Record<string, Plan>>({});
  const [usage, setUsage] = useState<Usage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [checkout, setCheckout] = useState("");
  const [message, setMessage] = useState("");
  const [authenticated, setAuthenticated] = useState(Boolean(localStorage.getItem("sona_token")));

  async function load() {
    setLoading(true); setError("");
    try {
      const planData = await api("/billing/plans");
      setPlans(planData.plans || {});
      try { const usageData = await api("/billing/usage"); setUsage(usageData.usage || null); setAuthenticated(true); }
      catch { setUsage(null); setAuthenticated(false); }
    } catch (e) { setError(e instanceof Error ? e.message : "Не удалось загрузить тарифы"); }
    finally { setLoading(false); }
  }
  useEffect(() => {
    void load();
    const params = new URLSearchParams(window.location.search);
    if (params.get("billing") === "success") {
      let cancelled = false;
      const poll = async () => { for (let i = 0; i < 8 && !cancelled; i++) { try { const data = await api("/billing/usage"); if (data?.usage) { setUsage(data.usage); setAuthenticated(true); if (data.usage.plan !== "free") { setMessage("Оплата получена. Тариф активирован."); window.history.replaceState({}, "", "/pricing"); return; } } } catch {} await new Promise(r => setTimeout(r, 1500)); } if (!cancelled) setMessage("Платёж создан. Активация тарифа может занять несколько секунд — обнови статус."); };
      void poll();
      return () => { cancelled = true; };
    }
  }, []);

  async function buy(plan: string) {
    if (!authenticated) { setMessage("Сначала войди в аккаунт. Нажми «Войти / Регистрация» в шапке SØNA."); return; }
    setCheckout(plan); setMessage("");
    try {
      const data = await api("/billing/checkout", { method: "POST", body: JSON.stringify({ plan, return_url: `${window.location.origin}${window.location.pathname}?billing=success` }) });
      localStorage.setItem("sona_pending_payment", data.payment_id || "");
      if (!data.confirmation_url) throw new Error("Платёжная ссылка не получена");
      window.location.href = data.confirmation_url;
    } catch (e) { setMessage(e instanceof Error ? e.message : "Не удалось открыть оплату"); setCheckout(""); }
  }

  const current = usage?.plan || "free";
  const order = ["free", "creator", "pro", "studio"].filter(k => plans[k]);
  return <div className="billing-page">
    <div className="billing-top"><button className="billing-logo" onClick={() => { window.history.pushState({}, "", "/"); window.dispatchEvent(new PopStateEvent("popstate")); }}><b>SØNA</b><span>MUSIC INTELLIGENCE</span></button><div className="billing-top-actions">{!authenticated && <button className="billing-login" onClick={() => { window.history.pushState({}, "", "/"); window.dispatchEvent(new PopStateEvent("popstate")); setTimeout(() => document.querySelector<HTMLButtonElement>(".account-button")?.click(), 80); }}>Войти / Регистрация</button>}<button className="billing-refresh" onClick={() => void load()} disabled={loading}><RefreshCw size={15} className={loading ? "spin" : ""}/> Обновить</button></div></div>
    <main className="billing-main">
      <section className="billing-hero"><span>SØNA PLANS</span><h1>Тарифы и AI-лимиты</h1><p>Выбирай объём работы, а SØNA автоматически учитывает использование инструментов в твоём месячном периоде.</p></section>
      {message && <div className="billing-message">{message}</div>}
      {error && <div className="billing-message">{error}<button onClick={() => void load()}>Повторить</button></div>}
      <section className="billing-grid">{loading && !order.length ? <div className="billing-loading"><RefreshCw className="spin"/> Загружаем тарифы…</div> : order.map(key => { const p = plans[key]; const features = Object.entries(p.features || {}); const isCurrent = authenticated && current === key; return <article className={`billing-card ${key === "pro" ? "featured" : ""}`} key={key}>
        {key === "pro" && <div className="billing-badge">SØNA PRO</div>}<span className="billing-eyebrow">{key.toUpperCase()}</span><h2>{p.name || key}</h2><div className="billing-price">{key === "free" ? "0 ₽" : <>{rub(p.price_rub)}<small>/мес</small></>}</div><div className="billing-current">{isCurrent ? "Текущий тариф" : key === "free" ? "Для знакомства" : "Для регулярной работы"}</div>
        <ul>{features.map(([name, value]) => <li key={name}><Check size={14}/><span>{prettyFeature(name)}</span><b>{value.limit}</b></li>)}</ul>{p.storage_mb ? <div className="billing-storage">Хранилище: {new Intl.NumberFormat("ru-RU").format(p.storage_mb)} MB</div> : null}
        {key === "free" ? <button className="billing-button secondary" disabled={isCurrent}>{isCurrent ? "Активен" : "Базовый"}</button> : <button className="billing-button" disabled={isCurrent || checkout === key} onClick={() => void buy(key)}>{checkout === key ? "Открываем оплату…" : isCurrent ? "Активен" : "Выбрать тариф"}<ArrowRight size={15}/></button>}
      </article>; })}</section>
      {usage && <section className="billing-usage"><div className="billing-usage-head"><div><span className="billing-eyebrow">CURRENT USAGE</span><h2>{usage.plan_name || current}</h2></div><span>{usage.subscription_status || "active"}{usage.period_end ? ` · до ${new Date(usage.period_end).toLocaleDateString("ru-RU")}` : ""}</span></div><div className="billing-usage-grid">{Object.entries(usage.features || {}).map(([key, item]) => { const used = Number(item.used || 0), limit = Number(item.limit || 0), percent = limit ? Math.min(100, used / limit * 100) : 0; return <div className="billing-usage-row" key={key}><div><span>{prettyFeature(key)}</span><b>{used} / {limit}</b></div><div className="billing-progress"><i style={{ width: `${percent}%` }}/></div></div>; })}</div></section>}
      {usage?.plan && usage.plan !== "free" && <div className="billing-note">Тариф активирован для этого аккаунта. Лимиты обновляются автоматически с началом нового периода.</div>}
    </main>
  </div>;
}
