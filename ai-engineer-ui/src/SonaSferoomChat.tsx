import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowUp, Bot, Mic, Music2, X } from "lucide-react";
import "./SonaSferoomChat.css";

type MusicReport = {
  status?: string;
  file?: string;
  technical?: { duration_sec?: number; bpm?: number; key?: string; time_signature?: string };
  mix?: { loudness?: { integrated_lufs?: number; true_peak_db?: number } };
  issues?: string[];
  priority_order?: string[];
};
type Message = { role: "assistant" | "user"; text: string; meta?: { agent?: string; skill?: string; tools?: string[]; musicReport?: MusicReport } };
type QuickAction = readonly [string, string, string];
const STORAGE_KEY = "sona_sferoom_messages";
const QUICK_ACTIONS: QuickAction[] = [
  ["ТЕКСТ ПЕСНИ", "Давай напишем текст песни", "songwriter"],
  ["AI СТУДИЯ", "Открой AI студию и помоги мне начать работу", "assistant"],
  ["АНАЛИЗ АУДИО", "Разбери мой трек: микс, динамика, LUFS и точки улучшения", "assistant"],
  ["МАСТЕРИНГ", "Подскажи, как сделать коммерческий мастер для этого трека", "assistant"],
  ["ТРЕНДЫ", "Найди актуальные музыкальные и social-тренды и преврати их в идеи", "release-marketing"],
  ["СТАТИСТИКА", "Разбери мою статистику и скажи, на что обратить внимание", "assistant"],
  ["ФИНАНСЫ", "Помоги разобраться с финансами музыкального проекта", "assistant"],
  ["ПРОЕКТ", "Помоги спланировать мой музыкальный проект от идеи до релиза", "release-marketing"],
  ["ТВОРЧЕСКИЙ ПОРТРЕТ", "Сделай мой творческий портрет как артиста", "songwriter"],
  ["КОНТЕНТ", "Составь контент-план для продвижения моего трека", "release-marketing"],
];
const initial: Message[] = [{ role: "assistant", text: "Ты в главном меню SØNA. Я могу помочь с текстом песни, созданием трека, анализом, мастерингом, трендами, статистикой, финансами, проектами, продвижением и творческим портретом. Куда двинемся?" }];

function MusicReportCard({ report }: { report: MusicReport }) {
  const technical = report.technical || {};
  const loudness = report.mix?.loudness || {};
  const issues = Array.isArray(report.issues) ? report.issues.filter(Boolean).slice(0, 3) : [];
  const priorities = Array.isArray(report.priority_order) ? report.priority_order.filter(Boolean).slice(0, 3) : [];
  const metric = (value: unknown, suffix = "") => typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(value % 1 ? 1 : 0)}${suffix}` : "—";
  return <div className="sona-music-report"><div className="sona-music-report-head"><span>UNIFIED INTELLIGENCE</span><strong>{report.file || "Текущий трек"}</strong></div><div className="sona-music-report-grid"><div><b>{metric(technical.bpm)}</b><small>BPM</small></div><div><b>{typeof technical.key === "string" ? technical.key : "—"}</b><small>ТОНАЛЬНОСТЬ</small></div><div><b>{metric(loudness.integrated_lufs, " LUFS")}</b><small>LOUDNESS</small></div><div><b>{metric(loudness.true_peak_db, " dB")}</b><small>TRUE PEAK</small></div></div>{issues.length > 0 && <div className="sona-music-report-list"><span>ТОЧКИ ВНИМАНИЯ</span>{issues.map((item, index) => <p key={`issue-${index}`}>{item}</p>)}</div>}{priorities.length > 0 && <div className="sona-music-report-list"><span>ПРИОРИТЕТЫ</span>{priorities.map((item, index) => <p key={`priority-${index}`}>{index + 1}. {item}</p>)}</div>}</div>;
}

export default function SonaSferoomChat() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>(() => { try { const raw = localStorage.getItem(STORAGE_KEY); const parsed = raw ? JSON.parse(raw) : null; return Array.isArray(parsed) && parsed.length ? parsed : initial; } catch { return initial; } });
  const [busy, setBusy] = useState(false);
  const [agent, setAgent] = useState("assistant");
  const scrollRef = useRef<HTMLDivElement>(null);
  const canSend = useMemo(() => input.trim().length > 0 && !busy, [input, busy]);
  useEffect(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-50))); }, [messages]);
  useEffect(() => { const el = scrollRef.current; if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" }); }, [messages, busy]);
  function followPointer(event: React.MouseEvent<HTMLElement>) { const rect = event.currentTarget.getBoundingClientRect(); event.currentTarget.style.setProperty("--mx", `${event.clientX - rect.left}px`); event.currentTarget.style.setProperty("--my", `${event.clientY - rect.top}px`); }
  async function sendText(value = input, selectedAgent = agent) {
    const text = value.trim(); if (!text || busy) return;
    const history = messages.slice(-20).map(({ role, text: messageText }) => ({ role, text: messageText }));
    setMessages(prev => [...prev, { role: "user", text }]); setInput(""); setBusy(true);
    try {
      const response = await fetch("/api/sona-chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: text, history, context: { product: "SØNA", language: "ru", client: "web", interface: "sferoom", agent: selectedAgent } }) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data?.detail || "Не удалось получить ответ");
      const tools = Array.isArray(data.tool_calls) ? data.tool_calls.map((item: { name?: unknown }) => typeof item?.name === "string" ? item.name : "").filter(Boolean) : [];
      setAgent(typeof data.agent === "string" ? data.agent : selectedAgent);
      setMessages(prev => [...prev, { role: "assistant", text: data.answer || "Не удалось получить ответ.", meta: { agent: data.agent, skill: data.skill, tools, musicReport: data.music_report } }]);
    } catch (error) { setMessages(prev => [...prev, { role: "assistant", text: error instanceof Error ? `Не удалось ответить: ${error.message}` : "Не удалось ответить. Попробуй ещё раз." }]); }
    finally { setBusy(false); }
  }
  return <div className={`sona-sferoom ${open ? "is-open" : ""}`}>{open ? <section className="sona-sferoom-panel" aria-label="SØNA Assistant" onMouseMove={followPointer}><div className="sona-sferoom-noise"/><header className="sona-sferoom-header"><div className="sona-sferoom-brand"><div className="sona-sferoom-avatar"><Bot size={19}/></div><div><strong>SØNA Assistant</strong><span><i/> Онлайн</span></div></div><button className="sona-sferoom-close" onClick={() => setOpen(false)} aria-label="Закрыть"><X size={20}/></button></header><div className="sona-sferoom-body" ref={scrollRef}>{messages.map((message, index) => <div key={`${message.role}-${index}`} className={`sona-sferoom-message ${message.role}`}>{message.text}{message.meta?.musicReport?.status === "ok" && <MusicReportCard report={message.meta.musicReport}/>} {message.meta && <small className="sona-sferoom-meta">{message.meta.agent ? `Агент: ${message.meta.agent}` : "SØNA"}{message.meta.tools?.length ? ` · Инструменты: ${message.meta.tools.join(", ")}` : ""}</small>}</div>)}{busy && <div className="sona-sferoom-message assistant typing"><span/><span/><span/></div>}</div><div className="sona-sferoom-actions">{QUICK_ACTIONS.map(([label, prompt, actionAgent]) => <button key={label} onClick={() => { setAgent(actionAgent); void sendText(prompt, actionAgent); }} disabled={busy}>{label}</button>)}</div><form className="sona-sferoom-composer" onSubmit={e => { e.preventDefault(); void sendText(); }}><button type="button" className="composer-icon" aria-label="Музыка"><Music2 size={18}/></button><button type="button" className="composer-icon" aria-label="Голос"><Mic size={18}/></button><input value={input} onChange={e => setInput(e.target.value)} placeholder="Напишите сообщение..." aria-label="Сообщение"/><button className="composer-send" type="submit" disabled={!canSend} aria-label="Отправить"><ArrowUp size={19}/></button></form><div className="sona-sferoom-disclaimer">SØNA может ошибаться. Проверяйте важную информацию.</div></section> : <button className="sona-sferoom-trigger" onClick={() => setOpen(true)} aria-label="Открыть SØNA Assistant"><Bot size={18}/><span>SØNA Assistant</span><i/></button>}</div>;
}
