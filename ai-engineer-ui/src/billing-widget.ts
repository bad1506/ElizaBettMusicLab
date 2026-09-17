const API = (import.meta as any).env?.VITE_API_URL || "/api";

type User = { id: string; name?: string; email?: string };
type Plan = { key: string; name?: string; price_rub?: number; features?: Record<string, { limit?: number }>; storage_mb?: number };

const KEY = "sona_token";
const PAYMENT_KEY = "sona_pending_payment";

function css() {
  if (document.getElementById("sona-billing-style")) return;
  const style = document.createElement("style");
  style.id = "sona-billing-style";
  style.textContent = `
#sona-account-root{position:fixed;right:22px;bottom:22px;z-index:9999;font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.sona-account-btn{border:1px solid rgba(20,20,20,.12);background:#171717;color:#fff;border-radius:999px;padding:11px 17px;font-size:13px;font-weight:700;cursor:pointer;box-shadow:0 12px 35px rgba(0,0,0,.16)}
.sona-overlay{position:fixed;inset:0;background:rgba(12,12,12,.42);backdrop-filter:blur(8px);display:flex;align-items:center;justify-content:center;padding:20px;z-index:10000}
.sona-modal{width:min(920px,100%);max-height:min(820px,92vh);overflow:auto;background:#f7f4f2;color:#171717;border:1px solid rgba(20,20,20,.1);border-radius:26px;box-shadow:0 30px 100px rgba(0,0,0,.25);padding:28px}
.sona-modal h2{margin:0 0 6px;font-size:28px;letter-spacing:-.04em}.sona-muted{color:#6d6967;font-size:14px}.sona-close{float:right;border:0;background:transparent;font-size:28px;cursor:pointer;line-height:1}
.sona-tabs{display:flex;gap:8px;margin:22px 0 16px}.sona-tab{border:1px solid rgba(20,20,20,.12);background:transparent;border-radius:10px;padding:9px 13px;cursor:pointer}.sona-tab.active{background:#171717;color:#fff}
.sona-input{width:100%;box-sizing:border-box;border:1px solid rgba(20,20,20,.14);background:#fff;border-radius:11px;padding:12px 13px;margin:7px 0;font:inherit}.sona-primary,.sona-plan button{border:0;background:#171717;color:#fff;border-radius:11px;padding:12px 15px;font-weight:700;cursor:pointer}.sona-primary:disabled,.sona-plan button:disabled{opacity:.45;cursor:not-allowed}
.sona-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:18px}.sona-plan{background:#fff;border:1px solid rgba(20,20,20,.1);border-radius:18px;padding:18px}.sona-plan h3{margin:0 0 5px;font-size:18px}.sona-price{font-size:25px;font-weight:800;margin:8px 0 13px}.sona-plan ul{padding-left:18px;color:#666;font-size:12px;line-height:1.7;min-height:88px}.sona-current{display:inline-block;font-size:11px;border-radius:999px;background:#eee;padding:4px 8px;margin-bottom:8px}
.sona-usage{margin-top:18px;background:#fff;border:1px solid rgba(20,20,20,.1);border-radius:18px;padding:18px}.sona-usage-row{display:grid;grid-template-columns:120px 1fr 100px;gap:12px;align-items:center;margin:10px 0;font-size:12px}.sona-bar{height:7px;border-radius:9px;background:#ece9e7;overflow:hidden}.sona-bar i{display:block;height:100%;background:#171717;border-radius:9px}.sona-msg{margin:12px 0;padding:11px 13px;border-radius:11px;background:#ece9e7;font-size:13px}.sona-danger{background:#f4dddd}.sona-account-actions{display:flex;gap:8px;justify-content:space-between;align-items:center;margin-top:18px}.sona-link{border:0;background:transparent;text-decoration:underline;cursor:pointer;padding:8px}.sona-small{font-size:11px;color:#777}
@media(max-width:760px){#sona-account-root{right:14px;bottom:14px}.sona-modal{padding:20px;border-radius:20px}.sona-grid{grid-template-columns:1fr}.sona-usage-row{grid-template-columns:90px 1fr 65px}}
`;
  document.head.appendChild(style);
}

async function request(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", headers.get("Content-Type") || "application/json");
  const token = localStorage.getItem(KEY);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API}${path}`, { ...options, headers });
  const text = await res.text();
  let data: any = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text }; }
  if (!res.ok) throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  return data;
}

function rub(value: number) { return new Intl.NumberFormat("ru-RU").format(value) + " ₽/мес"; }
function esc(value: unknown) { return String(value ?? "").replace(/[&<>\"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[ch] || ch)); }

function root() {
  let node = document.getElementById("sona-account-root");
  if (!node) { node = document.createElement("div"); node.id = "sona-account-root"; document.body.appendChild(node); }
  return node;
}

async function loadMe() { try { return await request("/auth/me"); } catch { return null; } }
async function loadPlans() { return (await request("/billing/plans")).plans as Record<string, Plan>; }
async function loadUsage() { return (await request("/billing/usage")).usage; }

function shell(title: string, body: string) {
  root().innerHTML = `<div class="sona-overlay" id="sona-overlay"><section class="sona-modal"><button class="sona-close" id="sona-close" aria-label="Close">×</button><h2>${title}</h2>${body}</section></div>`;
  document.getElementById("sona-close")?.addEventListener("click", close);
  document.getElementById("sona-overlay")?.addEventListener("click", e => { if (e.target === e.currentTarget) close(); });
}
function close() { root().innerHTML = `<button class="sona-account-btn" id="sona-open">SØNA Account</button>`; document.getElementById("sona-open")?.addEventListener("click", open); }

function authView(tab: "login" | "register", message = "") {
  shell("SØNA Account", `<p class="sona-muted">Войди или создай аккаунт, чтобы использовать персональные лимиты и оплату.</p>
    <div class="sona-tabs"><button class="sona-tab ${tab === "login" ? "active" : ""}" id="tab-login">Войти</button><button class="sona-tab ${tab === "register" ? "active" : ""}" id="tab-register">Регистрация</button></div>
    ${message ? `<div class="sona-msg sona-danger">${esc(message)}</div>` : ""}
    <form id="sona-auth-form"><input class="sona-input" id="sona-name" placeholder="Имя" ${tab === "login" ? "style=\"display:none\"" : ""}/><input class="sona-input" id="sona-email" type="email" placeholder="Email" required/><input class="sona-input" id="sona-password" type="password" minlength="8" placeholder="Пароль (минимум 8 символов)" required/><button class="sona-primary" type="submit">${tab === "login" ? "Войти" : "Создать аккаунт"}</button></form>`);
  document.getElementById("tab-login")?.addEventListener("click", () => authView("login"));
  document.getElementById("tab-register")?.addEventListener("click", () => authView("register"));
  document.getElementById("sona-auth-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    const email = (document.getElementById("sona-email") as HTMLInputElement).value.trim();
    const password = (document.getElementById("sona-password") as HTMLInputElement).value;
    const name = (document.getElementById("sona-name") as HTMLInputElement).value.trim();
    try {
      const data = await request(tab === "login" ? "/auth/login" : "/auth/register", { method: "POST", body: JSON.stringify({ name, email, password }) });
      if (data.token) localStorage.setItem(KEY, data.token);
      await accountView();
    } catch (err) { authView(tab, String(err).replace(/^Error:\s*/, "")); }
  });
}

async function accountView() {
  const me = await loadMe();
  if (!me) { authView("login"); return; }
  const usage = me.billing || await loadUsage();
  const name = me.user?.name || me.user?.email || "Account";
  const plan = usage.plan_name || usage.plan || "Free";
  shell("Личный кабинет", `<p class="sona-muted">${esc(name)} · тариф <b>${esc(plan)}</b></p>
    <div class="sona-usage"><b>Использование</b><div id="sona-usage-list">${usageRows(usage)}</div></div>
    <div class="sona-grid" id="sona-plans"><div class="sona-muted">Загрузка тарифов…</div></div>
    <div class="sona-account-actions"><button class="sona-link" id="sona-logout">Выйти</button><span class="sona-small">Оплата открывается на защищённой странице ЮKassa.</span></div>`);
  document.getElementById("sona-logout")?.addEventListener("click", async () => { try { await request("/auth/logout", { method: "POST" }); } catch {} localStorage.removeItem(KEY); localStorage.removeItem(PAYMENT_KEY); close(); });
  try { renderPlans(await loadPlans(), usage.plan); } catch (err) { document.getElementById("sona-plans")!.innerHTML = `<div class="sona-msg sona-danger">${esc(String(err).replace(/^Error:\s*/, ""))}</div>`; }
}

function usageRows(usage: any) {
  const features = usage?.features || {};
  const entries = Object.entries(features) as [string, any][];
  if (!entries.length) return `<div class="sona-muted">Лимиты пока не загружены.</div>`;
  return entries.map(([key, item]) => {
    const used = Number(item?.used || 0), limit = Number(item?.limit || 0), pct = limit > 0 ? Math.min(100, Math.round(used / limit * 100)) : 0;
    return `<div class="sona-usage-row"><span>${esc(key)}</span><div class="sona-bar"><i style="width:${pct}%"></i></div><span>${used}/${limit}</span></div>`;
  }).join("");
}

function renderPlans(plans: Record<string, Plan>, current: string) {
  const host = document.getElementById("sona-plans"); if (!host) return;
  const order = ["creator", "pro", "studio"];
  host.innerHTML = order.filter(key => plans[key]).map(key => {
    const p = plans[key]; const limits = Object.entries(p.features || {}).slice(0, 4).map(([k, v]: any) => `<li>${esc(k)}: ${esc(v.limit)}</li>`).join("");
    return `<article class="sona-plan">${current === key ? `<span class="sona-current">Текущий тариф</span>` : ""}<h3>${esc(p.name || key)}</h3><div class="sona-price">${p.price_rub ? rub(p.price_rub) : "Цена не настроена"}</div><ul>${limits}</ul><button data-plan="${esc(key)}" ${current === key ? "disabled" : ""}>${current === key ? "Активен" : "Выбрать тариф"}</button></article>`;
  }).join("");
  host.querySelectorAll<HTMLButtonElement>("button[data-plan]").forEach(btn => btn.addEventListener("click", () => checkout(btn.dataset.plan!)));
}

async function checkout(plan: string) {
  const returnUrl = `${window.location.origin}${window.location.pathname}?billing=success`;
  try {
    const data = await request("/billing/checkout", { method: "POST", body: JSON.stringify({ plan, return_url: returnUrl }) });
    localStorage.setItem(PAYMENT_KEY, data.payment_id || "");
    window.location.href = data.confirmation_url;
  } catch (err) {
    const msg = String(err).replace(/^Error:\s*/, "");
    const node = document.querySelector(".sona-modal"); if (node) { const old = node.querySelector(".sona-msg"); old?.remove(); node.insertAdjacentHTML("afterbegin", `<div class="sona-msg sona-danger">${esc(msg)}</div>`); }
  }
}

async function checkReturn() {
  if (!new URLSearchParams(window.location.search).has("billing")) return;
  localStorage.getItem(PAYMENT_KEY);
  for (let i = 0; i < 6; i++) {
    const me = await loadMe();
    if (me?.billing && me.billing.plan !== "free") { await accountView(); return; }
    await new Promise(r => setTimeout(r, 1500));
  }
  await accountView();
}

async function open() {
  css();
  const me = await loadMe();
  if (me) await accountView(); else authView("login");
}

function mount() {
  css();
  close();
  void checkReturn();
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
