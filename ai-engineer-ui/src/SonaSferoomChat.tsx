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
type MusicTimelineSection = {
  index?: number;
  start_sec?: number;
  end_sec?: number;
  duration_sec?: number;
  role?: string;
  label?: string;
};
type MusicActionReport = {
  status?: string;
  file?: string;
  section?: { start_sec?: number; end_sec?: number; duration_sec?: number };
  timeline?: { duration_sec?: number | null; sections?: MusicTimelineSection[] };
  section_selection?: { mode?: string; selected_index?: number; selected_role_hint?: string };
  vocal?: { median_voiced_percent?: number | null };
  metrics?: { band_delta_percentage_points_vs_outside?: Record<string, number>; section_lufs?: number | null; outside_lufs?: number | null; stereo_correlation?: number | null; transient_count?: number };
  diagnosis?: Array<{ cause?: string; severity?: string; evidence?: string; recommendation?: string }>;
  recommended_order?: string[];
  limitations?: string[];
};
type Message = { role: "assistant" | "user"; text: string; meta?: { agent?: string; skill?: string; tools?: string[]; musicReport?: MusicReport; musicActionReport?: MusicActionReport; musicActionTool?: string } };
type QuickAction = readonly [string, string, string];
type ReportAction = readonly [string, string];
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
const REPORT_ACTIONS: ReportAction[] = [
  ["РАЗОБРАТЬ ВОКАЛ", "Разбери вокал текущего трека: найди самый проблемный участок или сильнейший припев, определи проблемы с интонацией, динамикой, таймингом и обработкой и дай конкретные шаги исправления. Ничего не изменяй в файле."],
  ["ИСПРАВИТЬ МИКС", "На основе текущего анализа трека составь конкретный план исправления микса: баланс, вокал, частотные конфликты, динамика, стерео и проблемные места. Если нужно, используй доступные read-only инструменты анализа. Не выполняй изменения и не перезаписывай файлы."],
  ["МАСТЕРИНГ", "На основе текущего анализа трека составь пошаговый коммерческий мастеринг-план с целями по loudness, true peak, динамике, тональному балансу и контролю артефактов. Укажи порядок действий и критерии проверки. Не выполняй мастеринг и не изменяй файлы."],
  ["ПОДРОБНЕЕ", "Подробно разъясни Unified Intelligence Report текущего трека: технические параметры, структуру, вокал, мелодию, микс, найденные проблемы и приоритеты. Объясни, что означает каждый важный показатель и что делать в первую очередь."],
];
const initial: Message[] = [{ role: "assistant", text: "Ты в главном меню SØNA. Я могу помочь с текстом песни, созданием трека, анализом, мастерингом, трендами, статистикой, финансами, проектами, продвижением и творческим портретом. Куда двинемся?" }];

function formatTime(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? `${Math.floor(value / 60)}:${String(Math.round(value % 60)).padStart(2, "0")}` : "—";
}
function MusicReportCard({ report, onAction }: { report: MusicReport; onAction: (prompt: string) => void }) {
  const technical = report.technical || {};
  const loudness = report.mix?.loudness || {};
  const issues = Array.isArray(report.issues) ? report.issues.filter(Boolean).slice(0, 3) : [];
  const priorities = Array.isArray(report.priority_order) ? report.priority_order.filter(Boolean).slice(0, 3) : [];
  const metric = (value: unknown, suffix = "") => typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(value % 1 ? 1 : 0)}${suffix}` : "—";
  return <div className="sona-music-report"><div className="sona-music-report-head"><span>UNIFIED INTELLIGENCE</span><strong>{report.file || "Текущий трек"}</strong></div><div className="sona-music-report-grid"><div><b>{metric(technical.bpm)}</b><small>BPM</small></div><div><b>{typeof technical.key === "string" ? technical.key : "—"}</b><small>ТОНАЛЬНОСТЬ</small></div><div><b>{metric(loudness.integrated_lufs, " LUFS")}</b><small>LOUDNESS</small></div><div><b>{metric(loudness.true_peak_db, " dB")}</b><small>TRUE PEAK</small></div></div>{issues.length > 0 && <div className="sona-music-report-list"><span>ТОЧКИ ВНИМАНИЯ</span>{issues.map((item, index) => <p key={`issue-${index}`}>{item}</p>)}</div>}{priorities.length > 0 && <div className="sona-music-report-list"><span>ПРИОРИТЕТЫ</span>{priorities.map((item, index) => <p key={`priority-${index}`}>{index + 1}. {item}</p>)}</div>}<div className="sona-music-report-buttons">{REPORT_ACTIONS.map(([label, prompt]) => <button key={label} type="button" onClick={() => onAction(prompt)}>{label}</button>)}</div></div>;
}

function MusicTimeline({ report, onSelect }: { report: MusicActionReport; onSelect: (start: number, end: number) => void }) {
  const sections = Array.isArray(report.timeline?.sections) ? report.timeline.sections.filter(item => typeof item.start_sec === "number" && typeof item.end_sec === "number" && item.end_sec > item.start_sec) : [];
  const actionStart = report.section?.start_sec;
  const actionEnd = report.section?.end_sec;
  const fallbackEnd = Math.max(0, ...sections.map(item => item.end_sec || 0), typeof actionEnd === "number" ? actionEnd : 0);
  const duration = typeof report.timeline?.duration_sec === "number" && report.timeline.duration_sec > 0 ? report.timeline.duration_sec : fallbackEnd;
  if (!duration) return null;
  const selectedStart = typeof actionStart === "number" ? actionStart : undefined;
  const selectedEnd = typeof actionEnd === "number" ? actionEnd : undefined;
  return <div className="sona-music-timeline"><div className="sona-music-timeline-head"><span>СТРУКТУРА ТРЕКА</span><small>{formatTime(duration)}</small></div><div className="sona-music-timeline-track" role="list" aria-label="Секции текущего трека">{sections.map((item, index) => { const start = Math.max(0, item.start_sec as number); const end = Math.min(duration, item.end_sec as number); const left = `${Math.min(100, start / duration * 100)}%`; const width = `${Math.max(1, (end - start) / duration * 100)}%`; const selected = selectedStart !== undefined && selectedEnd !== undefined && Math.abs(start - selectedStart) < 0.15 && Math.abs(end - selectedEnd) < 0.15; return <button key={`timeline-${item.index ?? index}-${start}`} type="button" role="listitem" className={`sona-music-timeline-segment ${selected ? "is-selected" : ""}`} style={{ left, width }} title={`${item.label || item.role || `Секция ${index + 1}`} · ${formatTime(start)} — ${formatTime(end)}`} onClick={() => onSelect(start, end)} aria-label={`Анализировать ${item.label || item.role || `секцию ${index + 1}`} с ${formatTime(start)} до ${formatTime(end)}`}><span>{item.label || item.role || `${index + 1}`}</span></button>; })}{selectedStart !== undefined && selectedEnd !== undefined && !sections.some(item => Math.abs((item.start_sec || 0) - selectedStart) < 0.15 && Math.abs((item.end_sec || 0) - selectedEnd) < 0.15) && <button type="button" className="sona-music-timeline-selection" style={{ left: `${Math.min(100, selectedStart / duration * 100)}%`, width: `${Math.max(1, Math.min(100, (selectedEnd - selectedStart) / duration * 100))}%` }} onClick={() => onSelect(selectedStart, selectedEnd)} aria-label={`Повторить анализ с ${formatTime(selectedStart)} до ${formatTime(selectedEnd)}`} title={`Выбранный участок · ${formatTime(selectedStart)} — ${formatTime(selectedEnd)}`} />}</div><div className="sona-music-timeline-labels"><span>0:00</span><span>{formatTime(duration)}</span></div><p>Нажмите на секцию, чтобы запустить отдельный анализ именно этого участка.</p></div>;
}

function MusicActionCard({ report, tool, onSelectSection }: { report: MusicActionReport; tool?: string; onSelectSection: (start: number, end: number) => void }) {
  if (report.status !== "ok") return null;
  const diagnosis = Array.isArray(report.diagnosis) ? report.diagnosis.slice(0, 4) : [];
  const recommendations = Array.isArray(report.recommended_order) ? report.recommended_order.slice(0, 4) : [];
  const section = report.section || {};
  const title = tool === "music.diagnose_vocal_in_section" ? "VOCAL DIAGNOSIS" : tool === "music.analyze_mix" ? "MIX DIAGNOSIS" : "MUSIC ACTION";
  return <div className="sona-music-action"><div className="sona-music-action-head"><span>{title}</span><strong>{report.file || "Текущий трек"}</strong></div><MusicTimeline report={report} onSelect={onSelectSection}/>{section.start_sec !== undefined && <div className="sona-music-action-section"><b>{formatTime(section.start_sec)} — {formatTime(section.end_sec)}</b><small>{report.section_selection?.selected_role_hint || "АНАЛИЗИРУЕМЫЙ УЧАСТОК"}</small></div>}{report.vocal?.median_voiced_percent != null && <div className="sona-music-action-vocal"><b>{report.vocal.median_voiced_percent.toFixed(0)}%</b><span>ВОКАЛЬНАЯ АКТИВНОСТЬ</span></div>}{diagnosis.length > 0 && <div className="sona-music-action-list"><span>ДИАГНОЗ</span>{diagnosis.map((item, index) => <div key={`diag-${index}`}><b>{item.severity || "info"} · {item.cause || "Причина"}</b>{item.evidence && <p>{item.evidence}</p>}{item.recommendation && <p>{item.recommendation}</p>}</div>)}</div>}{recommendations.length > 0 && <div className="sona-music-action-list"><span>ПОРЯДОК ИСПРАВЛЕНИЯ</span>{recommendations.map((item, index) => <p key={`rec-${index}`}>{index + 1}. {item}</p>)}</div>}</div>;
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
      setMessages(prev => [...prev, { role: "assistant", text: data.answer || "Не удалось получить ответ.", meta: { agent: data.agent, skill: data.skill, tools, musicReport: data.music_report, musicActionReport: data.music_action_report, musicActionTool: data.music_action_tool } }]);
    } catch (error) { setMessages(prev => [...prev, { role: "assistant", text: error instanceof Error ? `Не удалось ответить: ${error.message}` : "Не удалось ответить. Попробуй ещё раз." }]); }
    finally { setBusy(false); }
  }
  function handleReportAction(prompt: string) { void sendText(prompt, "assistant"); }
  function handleTimelineSelect(start: number, end: number) { void sendText(`Разбери вокал строго в участке ${start.toFixed(2)}–${end.toFixed(2)} секунд текущего трека. Используй read-only диагностику music.diagnose_vocal_in_section с section_start_sec=${start.toFixed(2)} и section_end_sec=${end.toFixed(2)}. Покажи конкретные проблемы, доказательства и порядок исправления. Ничего не изменяй в файле.`, "assistant"); }
  return <div className={`sona-sferoom ${open ? "is-open" : ""}`}>{open ? <section className="sona-sferoom-panel" aria-label="SØNA Assistant" onMouseMove={followPointer}><div className="sona-sferoom-noise"/><header className="sona-sferoom-header"><div className="sona-sferoom-brand"><div className="sona-sferoom-avatar"><Bot size={19}/></div><div><strong>SØNA Assistant</strong><span><i/> Онлайн</span></div></div><button className="sona-sferoom-close" onClick={() => setOpen(false)} aria-label="Закрыть"><X size={20}/></button></header><div className="sona-sferoom-body" ref={scrollRef}>{messages.map((message, index) => <div key={`${message.role}-${index}`} className={`sona-sferoom-message ${message.role}`}>{message.text}{message.meta?.musicReport?.status === "ok" && <MusicReportCard report={message.meta.musicReport} onAction={handleReportAction}/>} {message.meta?.musicActionReport?.status === "ok" && <MusicActionCard report={message.meta.musicActionReport} tool={message.meta.musicActionTool} onSelectSection={handleTimelineSelect}/>} {message.meta && <small className="sona-sferoom-meta">{message.meta.agent ? `Агент: ${message.meta.agent}` : "SØNA"}{message.meta.tools?.length ? ` · Инструменты: ${message.meta.tools.join(", ")}` : ""}</small>}</div>)}{busy && <div className="sona-sferoom-message assistant typing"><span/><span/><span/></div>}</div><div className="sona-sferoom-actions">{QUICK_ACTIONS.map(([label, prompt, actionAgent]) => <button key={label} onClick={() => { setAgent(actionAgent); void sendText(prompt, actionAgent); }} disabled={busy}>{label}</button>)}</div><form className="sona-sferoom-composer" onSubmit={e => { e.preventDefault(); void sendText(); }}><button type="button" className="composer-icon" aria-label="Музыка"><Music2 size={18}/></button><button type="button" className="composer-icon" aria-label="Голос"><Mic size={18}/></button><input value={input} onChange={e => setInput(e.target.value)} placeholder="Напишите сообщение..." aria-label="Сообщение"/><button className="composer-send" type="submit" disabled={!canSend} aria-label="Отправить"><ArrowUp size={19}/></button></form><div className="sona-sferoom-disclaimer">SØNA может ошибаться. Проверяйте важную информацию.</div></section> : <button className="sona-sferoom-trigger" onClick={() => setOpen(true)} aria-label="Открыть SØNA Assistant"><Bot size={18}/><span>SØNA Assistant</span><i/></button>}</div>;
}
