import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowUp, Bot, Mic, Music2, X } from "lucide-react";
import "./SonaSferoomChat.css";

type Message = { role: "assistant" | "user"; text: string };
const STORAGE_KEY = "sona_sferoom_messages";
const QUICK_ACTIONS = [
  ["ТЕКСТ ПЕСНИ", "Давай напишем текст песни", "songwriter"],
  ["AI СТУДИЯ", "Открой AI студию и помоги мне начать работу", "assistant"],
  ["СТАТИСТИКА", "Разбери мою статистику и скажи, на что обратить внимание", "audio-analysis"],
  ["ФИНАНСЫ", "Помоги разобраться с финансами музыкального проекта", "projects"],
  ["ТВОРЧЕСКИЙ ПОРТРЕТ", "Сделай мой творческий портрет как артиста", "songwriter"],
  ["КОНТЕНТ", "Составь контент-план для продвижения моего трека", "release-marketing"],
] as const;
const initial: Message[] = [{ role: "assistant", text: "Ты в главном меню SØNA. Я могу помочь с текстом песни, созданием трека, анализом, статистикой, финансами, продвижением и творческим портретом. Куда двинемся?" }];

export default function SonaSferoomChat() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>(() => { try { const raw = localStorage.getItem(STORAGE_KEY); const parsed = raw ? JSON.parse(raw) : null; return Array.isArray(parsed) && parsed.length ? parsed : initial; } catch { return initial; } });
  const [busy, setBusy] = useState(false);
  const [skill, setSkill] = useState("assistant");
  const scrollRef = useRef<HTMLDivElement>(null);
  const canSend = useMemo(() => input.trim().length > 0 && !busy, [input, busy]);
  useEffect(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-50))); }, [messages]);
  useEffect(() => { const el = scrollRef.current; if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" }); }, [messages, busy]);

  async function sendText(value = input, selectedSkill = skill) {
    const text = value.trim(); if (!text || busy) return;
    const history = messages.slice(-20); setMessages(prev => [...prev, { role: "user", text }]); setInput(""); setBusy(true);
    try {
      const response = await fetch("/api/sona-chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: text, history, context: { product: "SØNA", language: "ru", client: "web", interface: "sferoom", skill: selectedSkill } }) });
      const data = await response.json().catch(() => ({})); if (!response.ok) throw new Error(data?.detail || "Не удалось получить ответ");
      setMessages(prev => [...prev, { role: "assistant", text: data.answer || "Не удалось получить ответ." }]);
    } catch (error) { setMessages(prev => [...prev, { role: "assistant", text: error instanceof Error ? `Не удалось ответить: ${error.message}` : "Не удалось ответить. Попробуй ещё раз." }]); }
    finally { setBusy(false); }
  }

  return <div className={`sona-sferoom ${open ? "is-open" : ""}`}>
    {open ? <section className="sona-sferoom-panel" aria-label="SØNA Assistant"><div className="sona-sferoom-noise"/><header className="sona-sferoom-header"><div className="sona-sferoom-brand"><div className="sona-sferoom-avatar"><Bot size={19}/></div><div><strong>SØNA Assistant</strong><span><i/> Онлайн</span></div></div><button className="sona-sferoom-close" onClick={() => setOpen(false)} aria-label="Закрыть"><X size={20}/></button></header><div className="sona-sferoom-body" ref={scrollRef}>{messages.map((message, index) => <div key={`${message.role}-${index}`} className={`sona-sferoom-message ${message.role}`}>{message.text}<small>{message.role === "assistant" ? "SØNA" : ""}</small></div>)}{busy && <div className="sona-sferoom-message assistant typing"><span/><span/><span/></div>}</div><div className="sona-sferoom-actions">{QUICK_ACTIONS.map(([label, prompt, actionSkill]) => <button key={label} onClick={() => { setSkill(actionSkill); void sendText(prompt, actionSkill); }} disabled={busy}>{label}</button>)}</div><form className="sona-sferoom-composer" onSubmit={e => { e.preventDefault(); void sendText(); }}><button type="button" className="composer-icon" aria-label="Музыка"><Music2 size={18}/></button><button type="button" className="composer-icon" aria-label="Голос"><Mic size={18}/></button><input value={input} onChange={e => setInput(e.target.value)} placeholder="Напишите сообщение..." aria-label="Сообщение"/><button className="composer-send" type="submit" disabled={!canSend} aria-label="Отправить"><ArrowUp size={19}/></button></form><div className="sona-sferoom-disclaimer">SØNA может ошибаться. Проверяйте важную информацию.</div></section> : <button className="sona-sferoom-trigger" onClick={() => setOpen(true)} aria-label="Открыть SØNA Assistant"><Bot size={18}/><span>SØNA Assistant</span><i/></button>}
  </div>;
}
