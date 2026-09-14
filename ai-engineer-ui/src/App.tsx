import { useRef, useState } from "react";
import { ArrowRight, AudioWaveform, Check, ChevronDown, ChevronRight, CirclePlay, Flame, Globe2, Menu, Music2, PenLine, Play, SlidersHorizontal, Sparkles, Upload, X, Zap } from "lucide-react";
import "./App.css";

type Tool = { id: string; title: string; description: string; icon: typeof Sparkles };
type Track = { title: string; genre: string; year: string; image: string };
const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const TELEGRAM_URL = "https://t.me/ElizaBettMusicLabBot?startapp";
const tools: Tool[] = [
  { id: "songwriter", title: "AI Songwriter", description: "Идеи, тексты, мелодии", icon: PenLine },
  { id: "analyzer", title: "Audio Analyzer", description: "Анализ трека, рекомендации", icon: AudioWaveform },
  { id: "master", title: "AI Mastering", description: "Профессиональный мастеринг с AI", icon: SlidersHorizontal },
  { id: "trends", title: "Trends", description: "Актуальные тренды, референсы, идеи", icon: Flame },
];
const tracks: Track[] = [
  { title: "Всё равно", genre: "POP", year: "2026", image: "https://images.unsplash.com/photo-1524250502761-1ac6f2e30d43?auto=format&fit=crop&w=900&q=85" },
  { title: "Тише", genre: "ACOUSTIC", year: "2026", image: "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=900&q=85" },
  { title: "Кукла Вуду", genre: "POP", year: "2026", image: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=900&q=85" },
  { title: "Новый мир", genre: "R&B", year: "2026", image: "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=900&q=85" },
];
const trends = [["01", "Atmospheric Pop", "Популярно в TikTok"], ["02", "Acoustic + AI Vocals", "Новый тренд"], ["03", "Dark Pop", "Растущая популярность"], ["04", "Русский поп 2.0", "В тренде"]];

export default function App() {
  const [page, setPage] = useState("home");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState("songwriter");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState("");
  const [request, setRequest] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  function go(next: string) { setPage(next); setMobileOpen(false); window.scrollTo({ top: 0, behavior: "smooth" }); }
  async function runTool() {
    if (!request.trim() && !file) return;
    setBusy(true); setResult("");
    try {
      if (selectedTool === "songwriter") {
        const res = await fetch(`${API}/songwriter`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request, mode: "SONG" }) });
        if (!res.ok) throw new Error(await res.text()); const data = await res.json(); setResult(data.answer || "Готово");
      } else if (selectedTool === "analyzer" && file) {
        const body = new FormData(); body.append("file", file); const res = await fetch(`${API}/upload`, { method: "POST", body });
        if (!res.ok) throw new Error(await res.text()); const data = await res.json(); setResult(JSON.stringify(data.analysis || data, null, 2));
      } else if (selectedTool === "master") {
        const res = await fetch(`${API}/master`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target_lufs: -10.5, ceiling_db: -1, intensity: "balanced", profile: "suno6_commercial" }) });
        if (!res.ok) throw new Error(await res.text()); const data = await res.json(); setResult(`Мастеринг завершён. Target: ${data.final_analysis?.lufs ?? "—"} LUFS`);
      } else if (selectedTool === "trends") {
        const res = await fetch(`${API}/songwriter/trends`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ focus: request || "Russian pop, TikTok, atmospheric pop" }) });
        if (!res.ok) throw new Error(await res.text()); const data = await res.json(); setResult(data.answer || JSON.stringify(data, null, 2));
      }
    } catch (error) { setResult(`Не удалось выполнить запрос: ${String(error).replace(/^Error:\s*/, "")}`); }
    finally { setBusy(false); }
  }
  return <div className="site-shell">
    <header className="site-header">
      <button className="brand" onClick={() => go("home")} aria-label="Eliza Bett Music Lab"><span className="brand-name">Eliza Bett</span><span className="brand-sub">MUSIC LAB</span></button>
      <nav className={mobileOpen ? "main-nav open" : "main-nav"}>{["Главная", "AI Инструменты", "Треки", "Проекты", "Тарифы", "О нас"].map(item => <button key={item} onClick={() => go(item === "Главная" ? "home" : item === "AI Инструменты" ? "tools" : item === "Треки" ? "tracks" : item === "Проекты" ? "projects" : item === "Тарифы" ? "pricing" : "about")}>{item}</button>)}</nav>
      <div className="header-actions"><button className="language"><Globe2 size={16} /> RU <ChevronDown size={12} /></button><button className="telegram" onClick={() => window.open(TELEGRAM_URL, "_blank")}>Открыть в Telegram <ArrowRight size={15} /></button></div>
      <button className="mobile-menu" onClick={() => setMobileOpen(v => !v)} aria-label="Меню">{mobileOpen ? <X /> : <Menu />}</button>
    </header>
    {page === "home" && <Home go={go} />}
    {page === "tools" && <ToolsPage selectedTool={selectedTool} setSelectedTool={setSelectedTool} request={request} setRequest={setRequest} file={file} setFile={setFile} busy={busy} result={result} runTool={runTool} inputRef={inputRef} />}
    {page === "tracks" && <TracksPage />}
    {page === "projects" && <SimplePage title="Проекты" subtitle="Все твои музыкальные идеи, треки и версии — в одном пространстве." action="Создать проект" />}
    {page === "pricing" && <PricingPage />}
    {page === "about" && <SimplePage title="О Eliza Bett Music Lab" subtitle="Пространство, где музыка встречается с искусственным интеллектом — от первой идеи до готового релиза." action="Начать сейчас" />}
  </div>;
}

function Home({ go }: { go: (page: string) => void }) {
  return <main>
    <section className="hero"><div className="hero-copy"><div className="micro">MUSIC <span>•</span> AI <span>•</span> CREATIVITY <span>•</span> NO LIMITS</div><h1>Eliza Bett<br /><em>Music Lab</em></h1><h2>Создавай. Анализируй. Улучшай. Выпускай.</h2><p>Все инструменты для твоей музыки — в одном месте.</p><div className="hero-buttons"><button className="dark-button" onClick={() => go("tools")}>Начать сейчас <ArrowRight size={17} /></button><button className="light-button"><CirclePlay size={19} /> Смотреть видео</button></div><div className="stats"><div><b>5K+</b><span>создано треков</span></div><div><b>98%</b><span>довольных авторов</span></div><div><b>∞</b><span>возможностей</span></div></div></div>
      <div className="hero-visual"><div className="phone-back"></div><div className="phone"><div className="phone-top">9:41 <span>● ● ●</span></div><div className="phone-brand">Eliza Bett<small>MUSIC LAB</small></div><div className="phone-disc"><span>Music<br />is a state<br />of mind</span></div><div className="phone-copy">Create<br />Better Music<small>AI tools for modern artists</small></div><div className="phone-start"><CirclePlay size={22} /> Start Now</div><div className="phone-nav"><span>⌂<small>Home</small></span><span>◷<small>Create</small></span><span>≋<small>Library</small></span><span>◯<small>Profile</small></span></div></div><div className="hero-note">TURN<br />IDEAS<br />INTO<br />MUSIC</div></div>
    </section>
    <section className="tool-strip">{tools.map(({ id, title, description, icon: Icon }) => <button className="feature-card" key={id} onClick={() => go("tools")}><Icon size={25} /><div><b>{title}</b><span>{description}</span></div><i><ArrowRight size={14} /></i></button>)}</section>
    <section className="telegram-banner"><div className="banner-copy"><span className="banner-kicker">✦</span><h3>Твоя музыка.<br />Без границ.</h3><p>Профессиональные AI-инструменты теперь доступны в Telegram.</p><button className="dark-button" onClick={() => window.open(TELEGRAM_URL, "_blank")}>Открыть в Telegram <ArrowRight size={15} /></button></div><div className="banner-image"></div><div className="mini-app"><span>TELEGRAM</span><h3>Music Lab<br />Mini App</h3><p>Создавай музыку прямо в Telegram. Всегда с тобой.</p><button onClick={() => window.open(TELEGRAM_URL, "_blank")}>Запустить Mini App <ArrowRight size={14} /></button></div></section>
    <section className="content-section"><div className="section-heading"><div><span>DISCOVER</span><h2>Последние треки</h2></div><button>Смотреть все <ArrowRight size={14} /></button></div><div className="bottom-grid"><div className="track-grid">{tracks.map(track => <article className="track-card" key={track.title}><div className="track-image" style={{ backgroundImage: `url(${track.image})` }}><button><Play size={14} fill="currentColor" /></button></div><div className="track-meta"><div><b>{track.title}</b><span>{track.genre} · {track.year}</span></div><button>•••</button></div></article>)}</div><div className="trends-panel"><div className="section-heading"><div><span>NOW</span><h2>Тренды сейчас</h2></div><button>Все <ArrowRight size={14} /></button></div>{trends.map(([number, title, sub]) => <div className="trend-row" key={number}><b>{number}</b><span className="trend-avatar"></span><div><strong>{title}</strong><small>{sub}</small></div><AudioWaveform size={20} /></div>)}</div></div></section>
    <footer className="footer"><div className="brand-footer">Eliza Bett<small>MUSIC LAB</small></div><div className="footer-links"><span>Конфиденциальность</span><span>Условия</span><span>Поддержка</span></div><div className="footer-social">◉　♪　◎　 <em>Music changes everything ♡</em></div></footer>
  </main>;
}

function ToolsPage({ selectedTool, setSelectedTool, request, setRequest, file, setFile, busy, result, runTool, inputRef }: { selectedTool: string; setSelectedTool: (v: string) => void; request: string; setRequest: (v: string) => void; file: File | null; setFile: (v: File | null) => void; busy: boolean; result: string; runTool: () => void; inputRef: React.RefObject<HTMLInputElement | null> }) {
  return <main className="tools-page"><div className="page-intro"><span>AI MUSIC WORKSPACE</span><h1>Инструменты для музыки</h1><p>От идеи до релиза. Выбери инструмент и начни работу.</p></div><div className="tool-layout"><aside className="tool-sidebar">{tools.map(({ id, title, description, icon: Icon }) => <button className={selectedTool === id ? "tool-nav active" : "tool-nav"} key={id} onClick={() => setSelectedTool(id)}><Icon size={19} /><span><b>{title}</b><small>{description}</small></span><ChevronRight size={14} /></button>)}</aside><section className="tool-workspace"><div className="workspace-head"><div><span>ELIZA BETT ENGINE</span><h2>{tools.find(t => t.id === selectedTool)?.title}</h2></div><span className="ready"><i></i> READY</span></div>{selectedTool === "analyzer" || selectedTool === "master" ? <button className="upload-zone" onClick={() => inputRef.current?.click()}><Upload size={28} /><b>{file ? file.name : "Загрузи аудиофайл"}</b><span>WAV, MP3, FLAC · до 100 MB</span></button> : null}<input ref={inputRef} type="file" accept="audio/*" hidden onChange={e => setFile(e.target.files?.[0] || null)} /><textarea className="tool-input" placeholder={selectedTool === "songwriter" ? "Расскажи, какую песню хочешь создать..." : "Опиши задачу или направление..."} value={request} onChange={e => setRequest(e.target.value)} /><button className="dark-button run-button" onClick={runTool} disabled={busy}>{busy ? "Обрабатываем..." : "Запустить AI"} <Zap size={15} /></button>{result && <pre className="result-box">{result}</pre>}</section></div></main>;
}
function TracksPage() { return <main className="generic-page"><span>LIBRARY</span><h1>Треки</h1><p>Музыка Eliza Bett Music Lab.</p><div className="track-grid large">{tracks.concat(tracks).map((track, i) => <article className="track-card" key={`${track.title}-${i}`}><div className="track-image" style={{ backgroundImage: `url(${track.image})` }}><button><Play size={14} fill="currentColor" /></button></div><div className="track-meta"><div><b>{track.title}</b><span>{track.genre} · {track.year}</span></div></div></article>)}</div></main>; }
function PricingPage() { return <main className="pricing-page"><div className="page-intro"><span>SIMPLE PRICING</span><h1>Выбери свой ритм</h1><p>Начни бесплатно и переходи на профессиональный уровень, когда будешь готов.</p></div><div className="pricing-grid">{[["FREE", "0 ₽", "Для знакомства"], ["PRO", "990 ₽", "Для активной работы"], ["STUDIO", "2 990 ₽", "Для профессионалов"]].map(([name, price, desc], i) => <article className={i === 1 ? "price-card featured" : "price-card"} key={name}><span>{name}</span><h2>{price}<small>/мес</small></h2><p>{desc}</p><ul><li><Check size={15} /> AI Songwriter</li><li><Check size={15} /> Audio Analyzer</li><li><Check size={15} /> AI Mastering</li><li><Check size={15} /> Projects & Library</li></ul><button className={i === 1 ? "dark-button" : "light-button"}>Начать <ArrowRight size={15} /></button></article>)}</div></main>; }
function SimplePage({ title, subtitle, action }: { title: string; subtitle: string; action: string }) { return <main className="simple-page"><span>ELIZA BETT MUSIC LAB</span><h1>{title}</h1><p>{subtitle}</p><button className="dark-button">{action} <ArrowRight size={16} /></button><div className="simple-orbit"><Music2 size={48} /></div></main>; }
