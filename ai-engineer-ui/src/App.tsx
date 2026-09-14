import { useMemo, useRef, useState } from "react";
import { ArrowRight, AudioWaveform, ChevronRight, Flame, Globe2, Menu, PenLine, Send, SlidersHorizontal, Sparkles, Upload, X, Zap } from "lucide-react";
import "./Chat.css";

type ToolId = "songwriter" | "analyzer" | "master" | "trends";
type Message = { role: "assistant" | "user"; text: string };
type Tool = { id: ToolId; title: string; description: string; icon: typeof Sparkles };
const API = import.meta.env.VITE_API_URL || (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" ? "http://127.0.0.1:8000" : "https://elizabettmusiclab-1.onrender.com");
const TELEGRAM_URL = import.meta.env.VITE_TELEGRAM_URL || "https://t.me/ElizaBettMusicLabBot?startapp";
const EXTENSIONS = ["wav", "mp3", "flac", "m4a", "ogg"];
const MAX_BYTES = 100 * 1024 * 1024;
const tools: Tool[] = [
  { id: "songwriter", title: "AI Songwriter", description: "Текст, идея, структура", icon: PenLine },
  { id: "analyzer", title: "Audio Analyzer", description: "Звук, баланс, проблемы", icon: AudioWaveform },
  { id: "master", title: "AI Mastering", description: "Мастеринг под задачу", icon: SlidersHorizontal },
  { id: "trends", title: "Trends", description: "Тренды и референсы", icon: Flame },
];
const initialMessages: Record<ToolId, Message[]> = {
  songwriter: [{ role: "assistant", text: "Я AI Songwriter. Опиши, что хочешь получить — тему, настроение, артиста, референс, язык, структуру. Я буду уточнять детали, пока результат не станет точным." }],
  analyzer: [{ role: "assistant", text: "Я Audio Analyzer. Загрузи трек и напиши, что тебя интересует: вокал, низ, стерео, громкость, клиппинг, баланс или подготовка к мастерингу. Разберём конкретно." }],
  master: [{ role: "assistant", text: "Я AI Mastering. Загрузи трек и скажи, каким должен быть результат: громкость, плотность, динамика, характер, референс. Перед запуском я зафиксирую параметры." }],
  trends: [{ role: "assistant", text: "Я Trends. Назови жанр, платформу, аудиторию или артиста — найду актуальное направление и превращу его в конкретные идеи для трека." }],
};

export default function App() {
  const [page, setPage] = useState("home");
  const [tool, setTool] = useState<ToolId>("songwriter");
  const [messages, setMessages] = useState<Record<ToolId, Message[]>>(initialMessages);
  const [input, setInput] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const currentTool = useMemo(() => tools.find((x) => x.id === tool)!, [tool]);
  const go = (next: string) => { setPage(next); setMobileOpen(false); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const add = (message: Message) => setMessages((all) => ({ ...all, [tool]: [...all[tool], message] }));
  async function readError(res: Response) { const text = await res.text(); try { const data = JSON.parse(text); return data.detail || data.message || text; } catch { return text || `HTTP ${res.status}`; } }
  function selectTool(id: ToolId) { setTool(id); setInput(""); }
  function selectAudio(next?: File) { if (!next) return; const ext = next.name.split(".").pop()?.toLowerCase() || ""; if (!EXTENSIONS.includes(ext)) { add({ role: "assistant", text: `Формат .${ext || "unknown"} не поддерживается. Используй WAV, MP3, FLAC, M4A или OGG.` }); return; } if (next.size > MAX_BYTES) { add({ role: "assistant", text: "Файл слишком большой. Максимальный размер — 100 MB." }); return; } setFile(next); add({ role: "assistant", text: `Файл «${next.name}» принят. Теперь скажи, какой результат нужен.` }); }
  async function uploadAudio() { if (!file) throw new Error("Сначала загрузи аудиофайл."); const body = new FormData(); body.append("file", file); const res = await fetch(`${API}/upload`, { method: "POST", body }); if (!res.ok) throw new Error(await readError(res)); return res.json(); }
  function context() { return messages[tool].slice(-8).map((m) => `${m.role === "user" ? "Клиент" : "AI"}: ${m.text}`).join("\n"); }
  async function send() {
    const text = input.trim(); if (!text || busy) return; add({ role: "user", text }); setInput(""); setBusy(true);
    try {
      if (tool === "songwriter") { const res = await fetch(`${API}/songwriter`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request: `${context()}\nКлиентская задача: ${text}`, mode: "SONG" }) }); if (!res.ok) throw new Error(await readError(res)); const data = await res.json(); add({ role: "assistant", text: data.answer || "Готово." }); }
      else if (tool === "trends") { const res = await fetch(`${API}/songwriter/trends`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ focus: `${context()}\nНовая задача: ${text}` }) }); if (!res.ok) throw new Error(await readError(res)); const data = await res.json(); add({ role: "assistant", text: data.report || data.answer || JSON.stringify(data, null, 2) }); }
      else if (tool === "analyzer") { const data = await uploadAudio(); add({ role: "assistant", text: formatAnalysis(data.analysis || data) }); }
      else if (tool === "master") { await uploadAudio(); const lufs = text.match(/-?\d+(?:[.,]\d+)?\s*LUFS/i)?.[0]?.replace(",", "."); const ceiling = text.match(/(?:ceiling|пик|потолок)[^\d-]*(-?\d+(?:[.,]\d+)?)/i)?.[1]?.replace(",", "."); const intensity = /плот|агрессив|громк/i.test(text) ? "aggressive" : /мяг|динами|натурал/i.test(text) ? "gentle" : "balanced"; const res = await fetch(`${API}/master`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target_lufs: lufs ? Number(lufs) : -10.5, ceiling_db: ceiling ? Number(ceiling) : -1, intensity, profile: "suno6_commercial" }) }); if (!res.ok) throw new Error(await readError(res)); const data = await res.json(); add({ role: "assistant", text: `Мастеринг завершён.\n\nTarget: ${data.final_analysis?.lufs ?? "—"} LUFS\nПрофиль: ${intensity}\nCeiling: ${ceiling ? `${ceiling} dB` : "-1 dB"}\n\nЕсли хочешь другой характер — напиши, например: «сделай мягче», «сделай плотнее» или «дай -9 LUFS».` }); }
    } catch (e) { add({ role: "assistant", text: `Не удалось выполнить запрос: ${String(e).replace(/^Error:\s*/, "")}` }); } finally { setBusy(false); }
  }
  return <div className="app"><header className="header"><button className="brand" onClick={() => go("home")}><b>Eliza Bett</b><span>MUSIC LAB</span></button><nav className={mobileOpen ? "nav open" : "nav"}>{[["Главная", "home"], ["AI Инструменты", "tools"], ["Треки", "tracks"], ["Проекты", "projects"], ["Тарифы", "pricing"], ["О нас", "about"]].map(([label, id]) => <button key={id} onClick={() => go(id)}>{label}</button>)}</nav><div className="head-actions"><span className="lang"><Globe2 size={14}/> RU</span><button className="telegram" onClick={() => window.open(TELEGRAM_URL, "_blank")}>Telegram <ArrowRight size={14}/></button><button className="menu" onClick={() => setMobileOpen(v => !v)}>{mobileOpen ? <X/> : <Menu/>}</button></div></header>
    {page === "home" && <Home go={go} />}
    {page === "tools" && <Workspace tool={tool} selectTool={selectTool} messages={messages[tool]} input={input} setInput={setInput} send={send} busy={busy} file={file} inputRef={inputRef} selectAudio={selectAudio} currentTool={currentTool} />}
    {page === "tracks" && <Simple title="Последние треки" text="Музыка, над которой ты работаешь, в одном месте." />}
    {page === "projects" && <Simple title="Проекты" text="Сохраняй идеи, версии, референсы и финальные мастера." />}
    {page === "pricing" && <Simple title="Тарифы" text="Выбери уровень AI-инструментов под свой объём работы." />}
    {page === "about" && <Simple title="Eliza Bett Music Lab" text="AI-пространство для музыканта — от идеи до готового релиза." />}
  </div>;
}
function Home({ go }: { go: (p: string) => void }) { return <main><section className="hero"><div><span className="eyebrow">MUSIC · AI · CREATIVITY</span><h1>Eliza Bett<br/><em>Music Lab</em></h1><p className="hero-title">Создавай. Анализируй. Улучшай. Выпускай.</p><p className="muted">Не четыре разрозненных инструмента, а один AI-диалог, который понимает задачу и доводит её до результата.</p><button className="primary" onClick={() => go("tools")}>Начать работу <ArrowRight size={17}/></button></div><div className="hero-art"><div className="orb">MUSIC<br/><i>LAB</i></div><div className="floating">AI<br/><span>WORKSPACE</span></div></div></section><section className="product-grid">{tools.map(t => <button key={t.id} onClick={() => go("tools")}><t.icon size={22}/><b>{t.title}</b><span>{t.description}</span><ArrowRight size={15}/></button>)}</section><section className="statement"><span>ONE WORKSPACE</span><h2>Клиент не должен угадывать,<br/>какой кнопкой получить результат.</h2><p>Он разговаривает с продуктом. AI задаёт уточняющие вопросы, фиксирует требования и возвращает следующую версию.</p></section></main> }
function Workspace({ tool, selectTool, messages, input, setInput, send, busy, file, inputRef, selectAudio, currentTool }: any) { return <main className="workspace-page"><div className="workspace-top"><div><span className="eyebrow">AI MUSIC WORKSPACE</span><h1>Работаем как в чате</h1><p>Каждая вкладка — отдельный продукт и отдельный контекст.</p></div><span className="status"><i/> ENGINE ONLINE</span></div><div className="workspace"><aside className="product-tabs">{tools.map(({ id, title, description, icon: Icon }: Tool) => <button className={tool === id ? "active" : ""} key={id} onClick={() => selectTool(id)}><Icon size={19}/><span><b>{title}</b><small>{description}</small></span><ChevronRight size={15}/></button>)}</aside><section className="chat"><div className="chat-head"><div><span>ELIZA BETT ENGINE</span><h2>{currentTool.title}</h2></div><span className="context-pill"><Sparkles size={13}/> Контекст сохраняется</span></div><div className="chat-body">{messages.map((m: Message, i: number) => <div className={m.role === "user" ? "bubble-row user" : "bubble-row"} key={i}><div className="avatar">{m.role === "user" ? "YOU" : "EB"}</div><div className="bubble">{m.text}</div></div>)}{busy && <div className="bubble-row"><div className="avatar">EB</div><div className="bubble typing"><i/><i/><i/></div></div>}</div><div className="composer"><div className="composer-tools">{(tool === "analyzer" || tool === "master") && <><input ref={inputRef} type="file" className="hidden" onChange={(e) => selectAudio(e.target.files?.[0])}/><button onClick={() => inputRef.current?.click()}><Upload size={15}/>{file ? file.name : "Загрузить аудио"}</button></>}{tool === "master" && <span className="hint"><Zap size={13}/> Можно написать «-9 LUFS, плотнее»</span>}</div><div className="input-row"><textarea value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder={tool === "songwriter" ? "Напиши, какой трек создаём..." : tool === "analyzer" ? "Что проверить в треке?" : tool === "master" ? "Каким должен быть мастер?" : "Какой тренд ищем?"}/><button className="send" onClick={send} disabled={busy || !input.trim()}>{busy ? <span className="spinner"/> : <Send size={17}/>}</button></div><small>Enter — отправить · Shift + Enter — новая строка</small></div></section></div></main> }
function formatAnalysis(data: any) { if (typeof data === "string") return data; const entries = Object.entries(data || {}).slice(0, 16); return entries.length ? entries.map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join("\n") : "Анализ готов, но backend не вернул метрики."; }
function Simple({ title, text }: { title: string; text: string }) { return <main className="simple"><span className="eyebrow">ELIZA BETT MUSIC LAB</span><h1>{title}</h1><p>{text}</p></main> }
