import { useEffect, useRef, useState } from "react";
import {
  Activity, AudioWaveform, BarChart3, BrainCircuit, Check, CheckCircle2, ChevronRight,
  CircleHelp, Download, FileAudio, Gauge, Headphones, Layers3, Library, Mic2, Package, Pause, PenLine,
  Play, Radio, RefreshCw, ShieldCheck, SlidersHorizontal, Sparkles, Upload, Waves, X, Zap
} from "lucide-react";
import "./App.css";

type Analysis = any;
type MasterResult = any;
type TimelineData = any;
const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const nav = [
  ["Overview", Activity], ["Production", Zap], ["Analyzer", Waves], ["Intelligence", BrainCircuit], ["Master", SlidersHorizontal],
  ["Songwriter", PenLine], ["Vocal", Mic2], ["Stems", Layers3], ["Reference", Library]
] as const;
const profiles: Record<string, { label: string; target: number; note: string }> = {
  suno6_commercial: { label: "Suno 6 · Commercial", target: -10.5, note: "AI-music commercial profile" },
  suno55_balanced: { label: "Suno 5.5 · Balanced", target: -11, note: "More restrained dynamics" },
  clean_streaming: { label: "Clean Streaming", target: -12, note: "Headroom-first profile" },
};
function num(v: unknown, digits = 2) { const n = Number(v); return Number.isFinite(n) ? n.toFixed(digits) : "—"; }
function clean(v: unknown) { return String(v ?? "").replaceAll("_", " "); }
function severity(v: unknown) { const n = Number(v); if (n >= .75) return "HIGH"; if (n >= .5) return "MED"; return typeof v === "string" ? v.toUpperCase() : "LOW"; }

export default function App() {
  const [active, setActive] = useState("Overview");
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [intelligence, setIntelligence] = useState<any | null>(null);
  const [master, setMaster] = useState<MasterResult | null>(null);
  const [masterIntelligence, setMasterIntelligence] = useState<any | null>(null);
  const [reference, setReference] = useState<Analysis | null>(null);
  const [originalTimeline, setOriginalTimeline] = useState<TimelineData | null>(null);
  const [masterTimeline, setMasterTimeline] = useState<TimelineData | null>(null);
  const [vocal, setVocal] = useState<any | null>(null);
  const [stems, setStems] = useState<Record<string, string> | null>(null);
  const [profile, setProfile] = useState("suno6_commercial");
  const [busy, setBusy] = useState({ upload: false, master: false, stems: false });
  const [error, setError] = useState("");
  const [chatOpen, setChatOpen] = useState(true);
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([
    { role: "assistant", text: "I’m ready. Load a track and I’ll translate the measurements into decisions: what I hear, why it matters, and what the engine will change." }
  ]);
  const [question, setQuestion] = useState("");
  const [writerMode, setWriterMode] = useState("SONG");
  const [writerRequest, setWriterRequest] = useState("");
  const [writerResult, setWriterResult] = useState("");
  const [trendResult, setTrendResult] = useState("");
  const [directorResult, setDirectorResult] = useState("");
  const [audioSongContext, setAudioSongContext] = useState<any | null>(null);
  const [melodyMap, setMelodyMap] = useState<any | null>(null);
  const [directorBusy, setDirectorBusy] = useState(false);
  const [production, setProduction] = useState<any | null>(null);
  const [productionBusy, setProductionBusy] = useState(false);
  const [projectBusy, setProjectBusy] = useState(false);
  const [projectBundle, setProjectBundle] = useState<string | null>(null);
  const [writerBusy, setWriterBusy] = useState(false);
  const [editorStage, setEditorStage] = useState("IDEA");
  const [songVersions, setSongVersions] = useState<{label:string;text:string}[]>([]);
  const [songAnalysis, setSongAnalysis] = useState<any | null>(null);
  const [writerMemory, setWriterMemory] = useState<any | null>(null);
  const [artistDna, setArtistDna] = useState<any | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [masterUrl, setMasterUrl] = useState<string | null>(null);
  const [preview, setPreview] = useState<"original" | "master">("original");
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const refRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => () => { if (audioUrl) URL.revokeObjectURL(audioUrl); }, [audioUrl]);
  useEffect(() => { void loadWriterMemory(); }, []);
  useEffect(() => { setPlaying(false); setProgress(0); if (audioRef.current) audioRef.current.load(); }, [preview, audioUrl, masterUrl]);
  const currentAudio = preview === "master" && masterUrl ? masterUrl : audioUrl || undefined;
  const a = analysis?.adaptive_analysis || {};
  const bands = a.band_energy_percent || {};
  const decisions = analysis?.decisions || [];
  const profileCfg = profiles[profile];
  const masterAnalysis = master?.final_analysis || {};

  useEffect(() => {
    if (!audioRef.current) return;
    const originalLufs = Number(a.lufs);
    const masteredLufs = Number(masterAnalysis.lufs);
    if (preview === "master" && Number.isFinite(originalLufs) && Number.isFinite(masteredLufs)) {
      const gain = Math.pow(10, Math.min(0, originalLufs - masteredLufs) / 20);
      audioRef.current.volume = Math.max(0.2, Math.min(1, gain));
    } else { audioRef.current.volume = 1; }
  }, [preview, a.lufs, masterAnalysis.lufs, currentAudio]);



  async function uploadTo(endpoint: string, selectedFile: File) {
    const body = new FormData(); body.append("file", selectedFile);
    const res = await fetch(`${API}/${endpoint}`, { method: "POST", body });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }
  async function loadTrack(selectedFile: File) {
    setError(""); setBusy(b => ({ ...b, upload: true })); setFile(selectedFile); setMaster(null); setMasterUrl(null); setReference(null); setStems(null); setIntelligence(null); setMasterIntelligence(null); setAudioSongContext(null); setMelodyMap(null); setPreview("original");
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(URL.createObjectURL(selectedFile));
    try {
      const data = await uploadTo("upload", selectedFile); setAnalysis(data.analysis); setIntelligence(data.analysis?.intelligence || null);
      const tr = await fetch(`${API}/timeline?source=original`); if (tr.ok) setOriginalTimeline(await tr.json());
      const ir = await fetch(`${API}/intelligence?source=original`); if (ir.ok) setIntelligence(await ir.json());
      const vr = await fetch(`${API}/vocal`); if (vr.ok) setVocal(await vr.json());
      const ar = await fetch(`${API}/songwriter/audio-context`); if (ar.ok) { const ad = await ar.json(); setAudioSongContext(ad.audio_context || null); } const mm = await fetch(`${API}/songwriter/melody-map`); if (mm.ok) { const md = await mm.json(); setMelodyMap(md.melody_map || null); }
      setActive("Overview");
    } catch (e) { setError(String(e).replace(/^Error:\s*/, "")); }
    finally { setBusy(b => ({ ...b, upload: false })); }
  }
  async function loadReference(selectedFile: File) {
    try { const data = await uploadTo("reference", selectedFile); setReference(data.analysis); setActive("Reference"); }
    catch (e) { setError(String(e).replace(/^Error:\s*/, "")); }
  }
  async function runMaster() {
    if (!analysis || busy.master) return;
    setError(""); setBusy(b => ({ ...b, master: true }));
    try {
      const res = await fetch(`${API}/master`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target_lufs: profileCfg.target, ceiling_db: -1, intensity: "balanced", profile }) });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json(); setMaster(data); setMasterIntelligence(data.final_intelligence || null);
      const tr = await fetch(`${API}/timeline?source=master`); if (tr.ok) setMasterTimeline(await tr.json());
      const ir = await fetch(`${API}/intelligence?source=master`); if (ir.ok) setMasterIntelligence(await ir.json());
      const name = data.final_output.split(/[\\/]/).pop(); setMasterUrl(`${API}/files/optimizer_output/${encodeURIComponent(name)}`);
      setPreview("master"); setActive("Master");
    } catch (e) { setError(String(e).replace(/^Error:\s*/, "")); }
    finally { setBusy(b => ({ ...b, master: false })); }
  }
  async function runStems() {
    if (!file || busy.stems) return;
    setBusy(b => ({ ...b, stems: true })); setError("");
    try { const res = await fetch(`${API}/stems`, { method: "POST" }); if (!res.ok) throw new Error(await res.text()); setStems((await res.json()).stems || {}); }
    catch (e) { setError(String(e).replace(/^Error:\s*/, "")); }
    finally { setBusy(b => ({ ...b, stems: false })); }
  }
  async function loadWriterMemory() {
    try { const res = await fetch(`${API}/songwriter/memory`); if (!res.ok) return; const data = await res.json(); setWriterMemory(data); setArtistDna(data.dna || null); } catch {}
  }
  async function analyzeWriterText(text = writerResult) {
    if (!text.trim() || writerBusy) return;
    try {
      const res = await fetch(`${API}/songwriter/analyze`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text}) });
      if (res.ok) { const data = await res.json(); setSongAnalysis(data.analysis || null); }
    } catch {}
  }
  function setWriterVersion(label:string, text:string) {
    setWriterResult(text);
    setSongVersions(v => [{label, text}, ...v.filter(x => x.label !== label)].slice(0, 8));
  }
  async function saveWriterDraft() {
    if (!writerResult.trim() || writerBusy) return;
    setWriterBusy(true); setError("");
    try {
      const res = await fetch(`${API}/songwriter/memory`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ title: displayTitle || "Untitled draft", text: writerResult, mode: writerMode, metadata:{track:displayTitle, profile} }) });
      if (!res.ok) throw new Error(await res.text()); const data=await res.json(); setArtistDna(data.dna || null); await loadWriterMemory();
    } catch(e) { setError(String(e).replace(/^Error:\s*/, "")); } finally { setWriterBusy(false); }
  }
  async function rebuildArtistDna() {
    if (writerBusy) return; setWriterBusy(true); setError("");
    try { const res=await fetch(`${API}/songwriter/dna/rebuild`,{method:"POST"}); if(!res.ok) throw new Error(await res.text()); const data=await res.json(); setArtistDna(data.dna || null); await loadWriterMemory(); }
    catch(e) { setError(String(e).replace(/^Error:\s*/, "")); } finally { setWriterBusy(false); }
  }

  async function runSongwriter(mode = writerMode) {
    if (!writerRequest.trim() || writerBusy) return;
    setWriterBusy(true); setError("");
    try {
      const res = await fetch(`${API}/songwriter`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request: writerRequest, mode, context: { track: displayTitle, profile, analysis: a, decisions: decisions.slice(0,8) }, trend_context: trendResult }) });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const answer = data.answer || "";
      setWriterResult(answer);
      setSongVersions(v => [{label: mode, text: answer}, ...v.filter(x => x.label !== mode)].slice(0, 8));
      void analyzeWriterText(answer);
    } catch (e) { setError(String(e).replace(/^Error:\s*/, "")); }
    finally { setWriterBusy(false); }
  }
  async function runDirector() {
    if (directorBusy) return;
    setDirectorBusy(true); setError("");
    try {
      const res = await fetch(`${API}/songwriter/direct`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request: writerRequest, context: { track: displayTitle, profile, analysis: a, vocal, decisions: decisions.slice(0,8), reference }, trend_context: trendResult }) });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json(); setDirectorResult(data.answer || "");
    } catch (e) { setError(String(e).replace(/^Error:\s*/, "")); }
    finally { setDirectorBusy(false); }
  }
  async function runProduction() {
    if (productionBusy || !analysis) return;
    setProductionBusy(true); setError("");
    try {
      const res = await fetch(`${API}/production/run`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ request: writerRequest, profile, target_lufs: profileCfg.target }) });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json(); setProduction(data);
      if (data.master) { setMaster(data.master); const name = data.master.final_output?.split(/[\\/]/).pop(); if (name) setMasterUrl(`${API}/files/optimizer_output/${encodeURIComponent(name)}`); }
      setDirectorResult(data.director?.answer || ""); setActive("Production");
    } catch(e) { setError(String(e).replace(/^Error:\s*/, "")); } finally { setProductionBusy(false); }
  }

  async function finalizeProject() {
    if (!analysis || projectBusy) return;
    setProjectBusy(true); setError("");
    try {
      const body = { name: displayTitle, brief: writerRequest, profile, lyrics: writerResult || directorResult, suno_prompt: directorResult || "", notes: production ? "Production Engine 10.0 result attached." : "" };
      const res = await fetch(`${API}/project/export`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setProjectBundle(data.url ? `${API}${data.url}` : null);
    } catch(e) { setError(String(e).replace(/^Error:\s*/, "")); } finally { setProjectBusy(false); }
  }

  async function runTrends() {
    if (writerBusy) return;
    setWriterBusy(true); setError("");
    try {
      const res = await fetch(`${API}/songwriter/trends`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ focus: writerRequest }) });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json(); setTrendResult(data.report || "");
    } catch (e) { setError(String(e).replace(/^Error:\s*/, "")); }
    finally { setWriterBusy(false); }
  }
  async function sendChat(text = question) {
    const q = text.trim(); if (!q) return; setQuestion(""); setMessages(m => [...m, { role: "user", text: q }]);
    try {
      const res = await fetch(`${API}/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q }) });
      if (!res.ok) throw new Error(await res.text()); const data = await res.json();
      setMessages(m => [...m, { role: "assistant", text: data.answer || "No response." }]);
    } catch (e) { setMessages(m => [...m, { role: "assistant", text: `Backend error: ${String(e).replace(/^Error:\s*/, "")}` }]); }
  }
  function togglePlay() { const el = audioRef.current; if (!el) return; if (el.paused) { void el.play(); setPlaying(true); } else { el.pause(); setPlaying(false); } }

  const displayTitle = file?.name || "No track loaded";
  const candidateRows = master?.candidates || [];

  return <div className="lab">
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><Radio size={15}/></div><div><b>ELIZA BETT</b><span>MUSIC LAB · 11.2</span></div></div>
      <div className="top-status"><span className="status-dot"/> LOCAL ENGINE <span className="divider"/> RTX / CUDA <span className="divider"/> {analysis ? "ANALYSIS READY" : "WAITING FOR AUDIO"}</div>
      <button className="top-help" title="Local audio intelligence"><CircleHelp size={16}/></button>
    </header>

    <div className="workspace">
      <aside className="sidebar">
        <div className="side-label">WORKSPACE</div>
        {nav.map(([label, Icon]) => <button key={label} className={`side-item ${active === label ? "active" : ""}`} onClick={() => setActive(label)}><Icon size={17}/><span>{label}</span>{label === "Master" && master && <i/>}</button>)}
        <div className="sidebar-bottom"><div className="engine-chip"><ShieldCheck size={13}/><span>ENGINE 11.0</span></div><small>LOCAL · PRIVATE</small></div>
      </aside>

      <main className="content">
        {active !== "Overview" && <>
          <section className="command-bar">
            <div><span className="eyebrow"><Sparkles size={12}/> AI MUSIC WORKSTATION</span><h1>{active}</h1><p>The same audio intelligence, focused on one stage of the workflow.</p></div>
            <div className="command-actions"><select className="profile-select" value={profile} onChange={e=>setProfile(e.target.value)} aria-label="Master profile"><option value="suno6_commercial">Suno 6 · Commercial</option><option value="suno55_balanced">Suno 5.5 · Balanced</option><option value="clean_streaming">Clean Streaming</option></select><button className="button primary" disabled={!analysis || productionBusy} onClick={runProduction}><Sparkles size={14}/>{productionBusy ? "BUILDING SONG" : "PRODUCE SONG"}</button><button className="button primary" disabled={!analysis || busy.master} onClick={runMaster}><Zap size={14}/>{busy.master ? "PROCESSING" : "AUTO MASTER"}</button><button className="button secondary" onClick={() => inputRef.current?.click()}><Upload size={14}/>{busy.upload ? "ANALYZING" : "LOAD TRACK"}</button></div>
          </section>
          <section className="player surface">
            <div className="track-id"><div className="track-icon"><AudioWaveform size={19}/></div><div><strong>{displayTitle}</strong><span>{analysis ? `${analysis.duration_sec}s · ${analysis.sample_rate} Hz` : "WAV · MP3 · FLAC · M4A · OGG"}</span></div></div>
            <button className="play-button" onClick={togglePlay} disabled={!currentAudio}>{playing ? <Pause size={17}/> : <Play size={17}/>}</button>
            <div className="timeline-wrap"><div className="timeline" onClick={e => { const r = e.currentTarget.getBoundingClientRect(); const t = ((e.clientX-r.left)/r.width)*(duration||1); if(audioRef.current){audioRef.current.currentTime=t;} }}><span style={{ width: `${progress}%` }}/></div><div className="time-row"><span>{Math.floor((duration||0)*progress/100/60).toString().padStart(2,"0")}:{Math.floor((duration||0)*progress/100%60).toString().padStart(2,"0")}</span><span>{Math.floor((duration||0)/60).toString().padStart(2,"0")}:{Math.floor((duration||0)%60).toString().padStart(2,"0")}</span></div></div>
            <div className="ab-toggle"><button className={preview === "original" ? "selected" : ""} onClick={() => setPreview("original")}>ORIGINAL</button><button className={preview === "master" ? "selected" : ""} disabled={!masterUrl} onClick={() => setPreview("master")}>MASTER</button><span className="level-match">{masterUrl ? "LUFS-MATCHED A/B" : "A/B READY AFTER MASTER"}</span></div>
            <audio ref={audioRef} src={currentAudio} onLoadedMetadata={e => setDuration(e.currentTarget.duration || 0)} onTimeUpdate={e => setProgress(e.currentTarget.duration ? (e.currentTarget.currentTime/e.currentTarget.duration)*100 : 0)} onEnded={() => setPlaying(false)}/>
          </section>
          <WaveformTimeline original={originalTimeline} master={masterTimeline} progress={progress} duration={duration} onSeek={(t:number) => { if(audioRef.current) audioRef.current.currentTime=t; }} />
        </>}

        {active === "Overview" && <HomeDashboard file={file} analysis={analysis} busy={busy} onUpload={() => inputRef.current?.click()} onMaster={runMaster} onNavigate={setActive} onPlay={togglePlay} playing={playing} currentAudio={currentAudio} audioRef={audioRef} duration={duration} progress={progress} setDuration={setDuration} setProgress={setProgress} />}

        {active === "Production" && <ProductionPage production={production} busy={productionBusy} run={runProduction} masterUrl={masterUrl} finalize={finalizeProject} projectBusy={projectBusy} projectBundle={projectBundle} />}

        {active === "Analyzer" && <Analyzer analysis={analysis} bands={bands} decisions={decisions}/>} 
        {active === "Intelligence" && <IntelligencePage intelligence={intelligence} masterIntelligence={masterIntelligence}/>}
        {active === "Songwriter" && <SongwriterPage audioSongContext={audioSongContext} melodyMap={melodyMap} mode={writerMode} setMode={setWriterMode} request={writerRequest} setRequest={setWriterRequest} result={writerResult} trend={trendResult} director={directorResult} directorBusy={directorBusy} busy={writerBusy} run={runSongwriter} direct={runDirector} trends={runTrends} save={saveWriterDraft} rebuild={rebuildArtistDna} dna={artistDna} memory={writerMemory}/>}
        {active === "Master" && <MasterPage master={master} profileCfg={profileCfg} runMaster={runMaster} busy={busy.master} masterUrl={masterUrl} masterAnalysis={masterAnalysis} candidateRows={candidateRows}/>} 
        {active === "Vocal" && <VocalPage vocal={vocal}/>} 
        {active === "Stems" && <StemsPage file={file} stems={stems} busy={busy.stems} runStems={runStems}/>} 
        {active === "Reference" && <ReferencePage reference={reference} master={master} refRef={refRef}/>} 

        <footer>ELIZA BETT MUSIC LAB · local audio intelligence · no proprietary Suno processing</footer>
      </main>

      {chatOpen ? <aside className="engineer surface"><div className="engineer-head"><div className="engineer-avatar"><BrainCircuit size={16}/></div><div><b>AI ENGINEER</b><span><i/> CONTEXT AWARE</span></div><button onClick={() => setChatOpen(false)}><X size={15}/></button></div><div className="engineer-context"><FileAudio size={14}/><div><b>{displayTitle}</b><span>{analysis ? `${decisions.length} decisions · ${num(a.lufs,1)} LUFS` : "Waiting for audio"}</span></div></div><div className="chat-body">{messages.map((m,i)=><div className={`msg ${m.role}`} key={i}>{m.text}</div>)}<div className="quick"><button onClick={() => void sendChat("What is the biggest problem in this mix?")}>Biggest issue</button><button onClick={() => void sendChat("Explain the master decision")}>Why this master?</button><button onClick={() => void sendChat("How close are we to the reference?")}>Reference</button></div></div><form className="chat-input" onSubmit={e => { e.preventDefault(); void sendChat(); }}><input value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ask about the mix…"/><button aria-label="Send"><ChevronRight size={15}/></button></form></aside> : <button className="chat-fab" onClick={() => setChatOpen(true)}><BrainCircuit size={17}/></button>}
    </div>
    <input ref={inputRef} hidden type="file" accept="audio/*,.wav,.mp3,.flac,.m4a,.ogg" onChange={e => { const f=e.target.files?.[0]; if(f) void loadTrack(f); e.currentTarget.value=""; }}/>
    <input ref={refRef} hidden type="file" accept="audio/*,.wav,.mp3,.flac,.m4a,.ogg" onChange={e => { const f=e.target.files?.[0]; if(f) void loadReference(f); e.currentTarget.value=""; }}/>
    {error && <div className="error-toast">{error}</div>}
  </div>;
}


function HomeDashboard({file, analysis, busy, onUpload, onMaster, onNavigate, onPlay, playing, currentAudio, audioRef, duration, progress, setDuration, setProgress}: any) {
  const projectName = file?.name ? file.name.replace(/\.[^/.]+$/, "") : "New Song";
  const bpm = analysis?.bpm || analysis?.adaptive_analysis?.bpm;
  const key = analysis?.key || analysis?.adaptive_analysis?.key || "Key estimate";
  const tools: [string, string, typeof Activity, string][] = [
    ["Music Analysis", "BPM, Key, Structure, Vocal, Energy", Waves, "Analyzer"],
    ["Songwriter", "Ideas, Lyrics, Trends, Artist DNA", PenLine, "Songwriter"],
    ["Song Director", "Full Concept & Suno Prompt", Sparkles, "Songwriter"],
    ["Production", "Audio-to-Song · Full Workflow", Zap, "Production"],
    ["Mastering", "AI Mastering Brain · Streaming Ready", SlidersHorizontal, "Master"],
  ];
  const recent = [
    {name: projectName, meta: `${bpm ? num(bpm,0) : "—"} BPM · ${clean(key)}`, cls:"recent-main"},
    {name: "Кукла Вуду", meta: "R&B · 118 BPM", cls:"recent-rose"},
    {name: "Всё Равно", meta: "Hip-Hop · 92 BPM", cls:"recent-night"},
  ];
  return <div className="home-dashboard">
    <div className="home-grid">
      <section className="hero-glass surface">
        <div className="hero-art"><div className="record-disc"/><div className="hero-script">Music<br/>Feels<br/>Different<br/>Here</div></div>
        <div className="hero-copy"><span className="eyebrow">ELIZA BETT MUSIC LAB · 11.2</span><h2>Your Music<br/><strong>Your Story</strong></h2><p>Turn a demo into a deliberate song — from first signal to final master.</p><div className="hero-actions"><button className="button primary" onClick={onUpload}><span>+</span> Create New Project</button><button className="button secondary" disabled={!file} onClick={() => onNavigate("Production")}><Library size={14}/> Open Project</button></div></div>
      </section>

      <aside className="home-side">
        <section className="mood-card surface"><div className="home-card-head"><b>Project Mood</b><span>See all →</span></div><div className="mood-row"><button className="mood active">Dreamy</button><button className="mood">Emotional</button><button className="mood">Dark</button></div><div className="mood-row"><button className="mood">Pop</button><button className="mood">R&B</button><button className="mood">Hip-Hop</button><button className="mood">Electronic</button><button className="mood add">+</button></div></section>
        <section className="current-card surface"><div className="current-art"><AudioWaveform size={25}/></div><div className="current-info"><span>Current Project</span><b>{projectName}</b><small>{bpm ? `${num(bpm,0)} BPM` : "— BPM"} · {clean(key)}</small></div><button className="mini-play" onClick={onPlay} disabled={!currentAudio}>{playing ? <Pause size={17}/> : <Play size={17}/>}</button><div className="mini-progress"><span style={{width:`${progress}%`}}/></div><div className="mini-times"><span>0:00</span><span>{duration ? `-${Math.max(0, duration - duration*progress/100).toFixed(2)}` : "-2:48"}</span></div></section>
      </aside>
    </div>

    <section className="tool-grid">{tools.map(([name,desc,Icon,target],i)=><button key={name} className={`tool-card surface ${i===4 ? "tool-featured" : ""}`} onClick={() => onNavigate(target as string)}><div className="tool-icon"><Icon size={19}/></div><div><b>{name}</b><p>{desc}</p></div><span className="tool-arrow">→</span></button>)}</section>

    <div className="home-lower">
      <section className="recent-card surface"><div className="home-card-head"><b>Recent Projects</b><button onClick={() => onNavigate("Production")}>View All →</button></div><div className="recent-grid">{recent.map((r:any)=><button key={r.name} className={`recent-project ${r.cls}`} onClick={() => r.name===projectName && file ? onNavigate("Analyzer") : onNavigate("Production")}><div className="recent-visual"><span>{r.name === projectName ? <AudioWaveform size={26}/> : r.name === "Кукла Вуду" ? "♡" : "◌"}</span></div><div className="recent-copy"><b>{r.name}</b><small>{r.meta}</small></div></button>)}<button className="recent-project new-project" onClick={onUpload}><div className="new-plus">+</div><b>New Project</b></button></div></section>
      <section className="quick-card surface"><div className="home-card-head"><b>Quick Actions</b></div><button onClick={onUpload}><Waves size={16}/> Analyze Audio <span>→</span></button><button onClick={() => onNavigate("Songwriter")}><PenLine size={16}/> Generate Lyrics <span>→</span></button><button onClick={() => onNavigate("Songwriter")}><Sparkles size={16}/> Create Suno Prompt <span>→</span></button><button disabled={!analysis || busy.master} onClick={onMaster}><SlidersHorizontal size={16}/> {busy.master ? "Mastering…" : "Master Track"} <span>→</span></button></section>
    </div>

    <section className="home-footer-player surface"><div className="footer-track"><div className="footer-cover"><AudioWaveform size={19}/></div><div><b>Eliza Bett Music Lab</b><span>Create · Analyze · Produce · Release</span></div></div><div className="footer-controls"><button>↶</button><button>‹</button><button className="footer-play" onClick={onPlay} disabled={!currentAudio}>{playing ? <Pause size={17}/> : <Play size={17}/>}</button><button>›</button><button>↷</button></div><div className="footer-volume"><Headphones size={16}/><div className="volume-line"><span/></div></div><div className="footer-quote">MUSIC IS A KIND OF FREEDOM <span>—</span></div></section>
    <audio ref={audioRef} src={currentAudio} onLoadedMetadata={e => setDuration(e.currentTarget.duration || 0)} onTimeUpdate={e => setProgress(e.currentTarget.duration ? (e.currentTarget.currentTime/e.currentTarget.duration)*100 : 0)} onEnded={() => {}}/>
  </div>;
}

function WaveformTimeline({ original, master, progress, duration, onSeek }: { original:any; master:any; progress:number; duration:number; onSeek:(t:number)=>void }) {
  const source = master || original;
  const peak = source?.waveform?.peak_db || [];
  const rms = source?.waveform?.rms_db || [];
  const loud = source?.loudness?.segments || [];
  const width = 1000;
  const height = 120;
  const points = peak.map((v:number,i:number) => { const x=i/(Math.max(1,peak.length-1))*width; const y=height/2 - (Math.max(-60,Math.min(0,v))+60)/60*48; return `${x.toFixed(1)},${y.toFixed(1)}`; }).join(" ");
  const points2 = rms.map((v:number,i:number) => { const x=i/(Math.max(1,rms.length-1))*width; const y=height/2 - (Math.max(-60,Math.min(0,v))+60)/60*34; return `${x.toFixed(1)},${y.toFixed(1)}`; }).join(" ");
  return <section className="surface timeline-panel"><div className="timeline-head"><div><span className="kicker">SIGNAL TIMELINE</span><h2>Waveform & loudness movement</h2></div><div className="timeline-legend"><span><i className="legend-wave"/> peak</span><span><i className="legend-rms"/> rms</span><span>{source ? `${loud.length} × ${source.loudness?.window_sec || 3}s` : "waiting"}</span></div></div>{source ? <><div className="waveform-box" onClick={e=>{const r=e.currentTarget.getBoundingClientRect(); onSeek(((e.clientX-r.left)/r.width)*(duration||source.duration_sec||1));}}><svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none"><polyline points={points} className="wave-peak"/><polyline points={points2} className="wave-rms"/><line x1={width*progress/100} x2={width*progress/100} y1="8" y2={height-8} className="playhead"/></svg></div><div className="loudness-track">{loud.map((seg:any,i:number)=>{ const min=-30,max=-5; const h=Math.max(4,Math.min(100,(Number(seg.lufs)-min)/(max-min)*100)); return <button key={i} title={`${seg.lufs} LUFS · ${seg.start}s`} style={{height:`${h}%`}} onClick={()=>onSeek(Number(seg.start))} aria-label={`Seek to ${seg.start} seconds`}/>})}</div><div className="timeline-axis"><span>0:00</span><span>{formatTime(source.duration_sec||duration)}</span></div></> : <Empty icon={<AudioWaveform size={20}/>} text="Load a track to generate the waveform and loudness timeline."/>}</section>;
}
function formatTime(sec:number){ const s=Math.max(0,Math.floor(Number(sec)||0)); return `${Math.floor(s/60)}:${String(s%60).padStart(2,"0")}`; }

function PanelHead({ kicker, title, icon }: { kicker:string; title:string; icon:React.ReactNode }) { return <div className="panel-head"><div><span className="kicker">{kicker}</span><h2>{title}</h2></div><span className="panel-icon">{icon}</span></div>; }
function Empty({ icon, text }: { icon:React.ReactNode; text:string }) { return <div className="empty"><span>{icon}</span><p>{text}</p></div>; }
function Decision({ d }: { d:any }) { return <div className="decision"><div className="decision-icon"><Waves size={14}/></div><div className="decision-main"><div className="decision-top"><b>{clean(d.problem || d.action || "TARGET")}</b><span>{severity(d.severity)}</span></div><p>{d.frequency_range || d.band || "adaptive band"}</p><small>{d.context || d.reason || "Adaptive signal detected relative to the track profile."}</small></div><strong>{d.gain_db != null ? `${Number(d.gain_db).toFixed(1)} dB` : "CONTROL"}</strong></div>; }
function IntelligencePage({ intelligence, masterIntelligence }: any) {
  const data = intelligence?.spectral?.segments || [];
  const stereo = intelligence?.stereo?.segments || [];
  const transients = intelligence?.transients || {};
  const vocal = intelligence?.vocal_events || {};
  const findings = intelligence?.findings || [];
  const spectralKeys = ["sub","bass","low_mid","mid","presence","high","air"];
  const colors: Record<string,string> = { sub:"#6f9ca6", bass:"#80b7c0", low_mid:"#91c9d1", mid:"#9edee5", presence:"#b4e9f0", high:"#8ecfd9", air:"#c7f6fb" };
  return <>
    <section className="surface panel intel-hero"><div><span className="kicker">AUDIO INTELLIGENCE 6.2</span><h2>See where the mix changes.</h2><p>Five-second evidence windows connect spectrum, stereo, transients and vocal behavior. These observations inform the engine; they do not blindly trigger processing.</p></div><div className="intel-count"><b>{findings.length}</b><span>FINDINGS</span></div></section>
    <section className="surface panel section-gap"><PanelHead kicker="SPECTRAL MOVEMENT" title="Energy by section" icon={<Waves size={16}/>}/>{data.length ? <div className="heatmap"><div className="heat-labels">{spectralKeys.map(k=><span key={k}>{k.replace("_"," ")}</span>)}</div><div className="heat-grid">{data.map((seg:any,i:number)=><div className="heat-col" key={i} title={`${seg.start}–${seg.end}s`}>{spectralKeys.map(k=><i key={k} style={{opacity:Math.min(.95,.12+Number(seg.bands?.[k]||0)/35),background:colors[k]}}/>)}<small>{formatTime(seg.start)}</small></div>)}</div></div> : <Empty icon={<Waves size={20}/>} text="Load a track to map spectral movement."/>}</section>
    <div className="intel-grid section-gap">
      <section className="surface panel"><PanelHead kicker="STEREO / PHASE" title="Field stability" icon={<Radio size={16}/>}/>{stereo.length ? <div className="intel-list">{stereo.slice(0,10).map((x:any,i:number)=><div className="intel-row" key={i}><span>{formatTime(x.start)}</span><div><b>Corr {num(x.correlation,2)}</b><small>width {num(x.width_db,1)} dB · side {num(x.side_percent,0)}%</small></div><em className={Number(x.correlation)<0.25?"risk":""}>{Number(x.correlation)<0.25?"CHECK":"STABLE"}</em></div>)}</div> : <Empty icon={<Radio size={20}/>} text="Stereo map is unavailable for mono audio."/>}</section>
      <section className="surface panel"><PanelHead kicker="TRANSIENT MAP" title="Rhythmic pressure" icon={<Activity size={16}/>}/><div className="transient-summary"><div><b>{num(transients.onsets_per_sec,2)}</b><span>ONSETS / SEC</span></div><div><b>{transients.peak_density ?? "—"}</b><span>PEAK / WINDOW</span></div></div><div className="mini-bars">{(transients.events||[]).map((x:any,i:number)=><i key={i} style={{height:`${Math.min(100, Number(x.count||0)*7+8)}%`}} title={`${x.start}s · ${x.count} onsets`}/>)}</div></section>
    </div>
    <section className="surface panel section-gap"><PanelHead kicker="VOCAL EVENTS" title="Pitch behavior across the mix" icon={<Mic2 size={16}/>}/>{vocal.status === "detected" ? <div className="vocal-events"><div className="vocal-event-head"><span>SECTION</span><span>VOICED</span><span>MEDIAN NOTE</span><span>DRIFT</span></div>{vocal.events?.slice(0,16).map((x:any,i:number)=><div className="vocal-event" key={i}><span>{formatTime(x.start)}–{formatTime(x.end)}</span><span>{num(x.voiced_percent,0)}%</span><span>{x.median_midi != null ? `${midiNote(x.median_midi)} · ${num(x.median_midi,1)}` : "—"}</span><span className={Number(x.pitch_drift)>0.22?"risk":""}>{num(x.pitch_drift,2)}</span></div>)}</div> : <Empty icon={<Mic2 size={20}/>} text="No confident full-mix pitch contour was detected."/>}</section>
    <section className="surface panel section-gap"><PanelHead kicker="FINDINGS" title="What deserves attention" icon={<Gauge size={16}/>}/>{findings.length ? <div className="finding-grid">{findings.map((f:any,i:number)=><div className={`finding ${f.severity}`} key={i}><div><b>{f.title}</b><span>{f.band}</span></div><strong>{String(f.severity).toUpperCase()}</strong><p>{f.reason}</p><small>{f.action}</small></div>)}</div> : <Empty icon={<CheckCircle2 size={20}/>} text="No elevated intelligence findings crossed the current thresholds."/>}</section>
    {masterIntelligence && <section className="surface panel section-gap"><PanelHead kicker="MASTER CHECK" title="After processing" icon={<CheckCircle2 size={16}/>}/><div className="master-intel-summary"><div><b>{masterIntelligence.summary?.finding_count ?? "—"}</b><span>FINDINGS AFTER MASTER</span></div><div><b>{masterIntelligence.summary?.high ?? 0}</b><span>HIGH</span></div><div><b>{masterIntelligence.summary?.medium ?? 0}</b><span>MEDIUM</span></div><div><b>{masterIntelligence.summary?.low ?? 0}</b><span>LOW</span></div></div></section>}
  </>;
}
function midiNote(midi:number){ try { const names=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]; const m=Math.round(Number(midi)); return `${names[(m%12+12)%12]}${Math.floor(m/12)-1}`; } catch { return "—"; } }

function Analyzer({ analysis, bands, decisions }: any) { return <><section className="surface panel"><PanelHead kicker="SPECTRAL INTELLIGENCE" title="Band profile" icon={<Waves size={16}/>}/>{analysis ? <div className="band-grid">{Object.entries(bands).map(([k,v])=><div className="band" key={k}><div><span>{clean(k)}</span><b>{num(v,2)}%</b></div><div className="band-track"><i style={{width:`${Math.min(100, Number(v)*4)}%`}}/></div></div>)}</div> : <Empty icon={<Waves size={20}/>} text="Load a track to inspect spectral energy."/>}</section><section className="surface panel section-gap"><PanelHead kicker="SIGNAL MAP" title="Decision context" icon={<Activity size={16}/>}/><div className="decision-list">{decisions.length ? decisions.map((d:any,i:number)=><Decision d={d} key={i}/>) : <Empty icon={<Gauge size={20}/>} text="No decision context yet."/>}</div></section></>; }
function SongwriterPage({ audioSongContext, melodyMap, mode, setMode, request, setRequest, result, setWriterResult, trend, director, directorBusy, busy, run, direct, trends, save, rebuild, dna, memory, editorStage, setEditorStage, songVersions, setWriterVersion, songAnalysis, setSongAnalysis, analyzeWriterText }: any) {
  const modes = [["IDEA","Ideas"],["HOOK","Hooks"],["CHORUS","Chorus"],["SONG","Full song"],["EDIT","Edit"],["RHYME","Rhyme"],["PROSODY","Prosody"],["TREND","Trend"]];
  const stages = [["IDEA","01"],["HOOK","02"],["CHORUS","03"],["VERSE","04"],["BRIDGE","05"],["FINAL","06"]];
  const songs = memory?.recent || [];
  const scores = [
    ["HOOK", result && songAnalysis?.scores?.hook_memorability],
    ["STRUCTURE", result && songAnalysis?.scores?.structure],
    ["SINGABILITY", result && songAnalysis?.scores?.singability],
    ["VARIETY", result && songAnalysis?.scores?.word_variety]
  ];
  const goStage = (stage:string) => {
    setEditorStage(stage);
    if (stage === "IDEA") setMode("IDEA");
    else if (stage === "HOOK") setMode("HOOK");
    else if (stage === "CHORUS") setMode("CHORUS");
    else if (stage === "VERSE") setMode("SONG");
    else if (stage === "BRIDGE") setMode("SONG");
    else if (stage === "FINAL") setMode("SONG");
  };
  return <>
    <section className="surface panel songwriter-hero studio-hero">
      <div><span className="kicker">ELIZA BETT SONGWRITER · 6.9</span><h2>Songwriter Studio.</h2><p>От идеи до финального текста: hook, припев, куплеты, bridge, редактура, prosody и версии. Агент помнит твой Artist DNA, но не копирует прошлые строки.</p></div>
      <div className="studio-progress"><b>{editorStage}</b><span>WRITING STAGE</span><i style={{width:`${((stages.findIndex(x=>x[0]===editorStage)+1)/stages.length)*100}%`}}/></div>
    </section>
    <section className="studio-steps surface panel">{stages.map(([id,n])=><button key={id} className={editorStage===id?"active":""} onClick={()=>goStage(id)}><small>{n}</small><b>{id}</b></button>)}</section>
    <section className="dna-strip surface panel">
      <div><span className="kicker">ARTIST DNA</span><b>{dna?.identity || "Профиль автора ещё не сформирован. Сохрани несколько черновиков."}</b></div>
      <div className="dna-tags">{(dna?.themes || []).slice(0,6).map((x:string)=><span key={x}>{x}</span>)}</div>
      <button className="button secondary" disabled={busy} onClick={()=>void rebuild()}>REBUILD DNA</button>
    </section>
    <section className="studio-main">
      <section className="surface panel studio-editor">
        <div className="output-head"><div><span className="kicker">EDITOR</span><h3>{editorStage === "FINAL" ? "Final lyric draft" : `${editorStage} workspace`}</h3></div><span className="output-state">VERSIONED</span></div>
        <div className="mode-row">{modes.map(([id,label]) => <button key={id} className={mode===id?"active":""} onClick={()=>{setMode(id);setEditorStage(id=== "SONG" ? "VERSE" : id)}}>{label}</button>)}</div>
        <label className="writer-label">BRIEF</label>
        <textarea className="brief-area" value={request} onChange={e=>setRequest(e.target.value)} placeholder="Тема, настроение, персонаж, точка зрения, BPM, жанр, ограничения или твой черновик…" />
        <div className="writer-actions"><button className="button primary" disabled={!request.trim() || busy} onClick={()=>void run(mode)}><PenLine size={14}/>{busy?"WORKING…":"BUILD STAGE"}</button><button className="button secondary" disabled={!result || busy} onClick={()=>void analyzeWriterText()}><Gauge size={14}/>ANALYZE</button><button className="button secondary" disabled={!result || busy} onClick={()=>void save()}>SAVE TO DNA</button></div>
        <div className="writer-suggestions"><span>QUICK START</span><button onClick={()=>setRequest("Тема: проблемы только в голове. Девушка поёт. Нужен контраст между тревогой в куплете и облегчением в припеве.")}>Mind vs reality</button><button onClick={()=>setRequest("Сделай hook из одной фразы, которую хочется повторить после первого прослушивания. Без клише.")}>Hook first</button><button onClick={()=>setRequest("Вот мой черновик. Сохрани смысл и сильные строки, но сократи строки, усили певучесть и убери клише:\n")}>Edit draft</button></div>
        {songVersions.length > 0 && <div className="version-strip"><span>VERSIONS</span>{songVersions.map((v,i)=><button key={v.label+i} onClick={()=>setWriterVersion(v.label,v.text)}>{v.label} {i===0?"· CURRENT":""}</button>)}</div>}
      </section>
      <section className="surface panel lyric-canvas">
        <div className="output-head"><div><span className="kicker">LYRIC CANVAS</span><h3>{mode === "SONG" ? "Editable song" : mode}</h3></div><span className="output-state">{result ? "LIVE" : "EMPTY"}</span></div>
        <textarea className="lyric-editor" value={result} onChange={e=>{setWriterResult(e.target.value); setSongAnalysis(null)}} placeholder="Здесь будет текст. После генерации его можно редактировать прямо в Canvas." />
        <div className="canvas-footer"><span>{result ? `${result.split(/\s+/).filter(Boolean).length} WORDS` : "0 WORDS"}</span><span>{result ? `${result.split(/\n/).filter(Boolean).length} LINES` : "0 LINES"}</span><span>{songAnalysis?.sections?.join(" → ") || "NO STRUCTURE ANALYZED"}</span></div>
      </section>
    </section>
    <section className="studio-analysis">
      <section className="surface panel score-panel"><div className="output-head"><div><span className="kicker">LYRIC QA</span><h3>Before release</h3></div><span className="output-state">HEURISTIC</span></div><div className="score-grid">{scores.map(([k,v])=><div key={k}><span>{k}</span><b>{v == null ? "—" : `${v}`}</b><i><em style={{width:`${Math.max(0,Math.min(100,Number(v)||0))}%`}}/></i></div>)}</div><p className="method-note">Это редакторская эвристика: она помогает находить места для проверки, но не заменяет прослушивание текста на мелодии.</p></section>
      <section className="surface panel structure-panel"><div className="output-head"><div><span className="kicker">STRUCTURE</span><h3>Song architecture</h3></div></div><div className="structure-flow">{(songAnalysis?.sections?.length ? songAnalysis.sections : ["VERSE","PRE-CHORUS","CHORUS","VERSE 2","BRIDGE","FINAL CHORUS"]).map((x:string,i:number)=><div key={i}><small>{String(i+1).padStart(2,"0")}</small><b>{x}</b></div>)}</div></section>
    </section>
    <section className="songwriter-memory-grid">
      <section className="surface panel memory-panel"><div className="output-head"><div><span className="kicker">AUTHOR MEMORY</span><h3>Recent drafts</h3></div><span className="output-state">{songs.length} SAVED</span></div>{songs.length ? songs.slice(0,6).map((x:any)=><div className="memory-row" key={x.id}><div><b>{x.title}</b><span>{x.mode} · {new Date(x.created_at).toLocaleDateString()}</span></div><small>{String(x.text||"").replace(/\s+/g," ").slice(0,130)}</small></div>) : <Empty icon={<Library size={20}/>} text="Save your first draft to start building Artist DNA."/>}</section>
      <section className="surface panel dna-panel"><div className="output-head"><div><span className="kicker">VOICE PROFILE</span><h3>What the agent remembers</h3></div></div><div className="dna-detail"><div><span>STRENGTHS</span><p>{(dna?.strengths||[]).join(" · ") || "—"}</p></div><div><span>AVOID</span><p>{(dna?.avoid||[]).join(" · ") || "—"}</p></div><div><span>SIGNATURE PHRASES</span><p>{(dna?.signature_phrases||[]).slice(0,4).join(" / ") || "—"}</p></div></div></section>
    </section>
    <section className="surface panel audio-context-panel"><div className="output-head"><div><span className="kicker">AUDIO → SONG · 6.9</span><h3>Write against the actual demo.</h3></div><span className="output-state">MEASURED + ESTIMATED</span></div><div className="audio-song-metrics"><div><span>BPM</span><b>{audioSongContext?.tempo?.bpm ? num(audioSongContext.tempo.bpm,1) : "—"}</b><small>{audioSongContext?.confidence?.tempo ? `${num(audioSongContext.confidence.tempo,0)}% conf.` : "not detected"}</small></div><div><span>KEY</span><b>{audioSongContext?.key?.key || "—"}</b><small>{audioSongContext?.key?.confidence ? `${num(audioSongContext.key.confidence,0)}% conf.` : "estimate"}</small></div><div><span>SECTIONS</span><b>{audioSongContext?.sections?.length ?? "—"}</b><small>candidate boundaries</small></div><div><span>BEATS</span><b>{audioSongContext?.tempo?.beat_count ?? "—"}</b><small>detected events</small></div></div><div className="audio-section-strip">{(audioSongContext?.sections || []).map((x:any,i:number)=><span key={i} title={`${x.start}–${x.end}s`}><b>{String(i+1).padStart(2,"0")}</b>{x.role_hint || x.energy_label || "SECTION"}<small>{formatTime(x.start)}–{formatTime(x.end)}</small></span>)}</div><p className="method-note">BPM и тональность — оценки из аудио; границы секций — кандидаты для аранжировочного планирования, а не гарантированная транскрипция.</p></section><section className="surface panel melody-panel"><div className="output-head"><div><span className="kicker">MELODY → LYRIC · 6.9</span><h3>Fit words to the actual vocal phrasing.</h3></div><span className="output-state">TIMING EVIDENCE</span></div><div className="melody-summary"><div><span>PHRASES</span><b>{melodyMap?.phrase_count ?? "—"}</b></div><div><span>VOICED</span><b>{melodyMap ? `${num((melodyMap.voiced_ratio||0)*100,0)}%` : "—"}</b></div><div><span>ALIGNMENT</span><b>{melodyMap?.status === "ok" ? "READY" : "—"}</b></div></div>{melodyMap?.phrases?.length ? <div className="phrase-strip">{melodyMap.phrases.slice(0,18).map((p:any,i:number)=><span key={i} title={`${p.start}–${p.end}s · ~${p.syllable_budget_estimate} syllables`}><b>{i+1}</b><small>{formatTime(p.start)}–{formatTime(p.end)}</small><em>~{p.syllable_budget_estimate} syl</em></span>)}</div> : <p className="method-note">После загрузки демо здесь появятся вероятные вокальные фразы и ориентировочная плотность текста.</p>}<p className="method-note">Фразы и syllable budgets — эвристические ориентиры, а не word-level transcription. Инструмент помогает не перегружать реальную мелодию текстом.</p></section><section className="surface panel director-panel"><div className="output-head"><div><span className="kicker">AI SONG DIRECTOR · 6.9</span><h3>Turn the track into a song plan.</h3></div><span className="output-state">AUDIO + DNA + TRENDS</span></div><p className="lead">Агент объединяет brief, анализ аудио, Vocal Intelligence, Artist DNA и свежие trend signals. На выходе — концепция, hook, структура, lyric draft, production direction и Suno-ready prompt.</p><div className="director-actions"><button className="button primary" disabled={directorBusy} onClick={()=>void direct()}><Sparkles size={14}/>{directorBusy?"DIRECTING…":"DIRECT SONG"}</button><span className="director-hint">Не обещает вирусность. Сначала проверяет контекст, затем предлагает оригинальное направление.</span></div>{director && <pre className="director-output">{director}</pre>}</section>

    <section className="surface panel trend-panel"><div className="output-head"><div><span className="kicker">TREND INTELLIGENCE</span><h3>Current signals → original directions</h3></div><span className="output-state">WEB RESEARCH</span></div><p className="lead">Тренды остаются отдельным слоем: агент исследует свежие сигналы, отделяет факты от inference и только потом предлагает направления, совместимые с Artist DNA.</p><pre className="trend-output">{trend || "Нажми REFRESH TRENDS. При наличии OPENAI_API_KEY агент сможет собрать свежий отчёт с источниками и датами."}</pre><button className="button secondary" disabled={busy} onClick={()=>void trends()}>REFRESH TRENDS</button></section>
    <section className="surface panel skill-panel"><div><span className="kicker">WRITING SKILLS</span><h3>Persistent creative stack</h3></div><div className="skill-grid">{["Hook strength","Chorus memorability","Story progression","Rhyme variety","Internal rhyme","Assonance","Prosody / stress","Singability","Concrete imagery","Cliché control","Emotional arc","Originality guardrails","Artist DNA","Draft memory","Trend synthesis","Anti-repetition"].map(x=><span key={x}>{x}</span>)}</div></section>
  </>;
}
function ProductionPage({ production, busy, run, masterUrl, finalize, projectBusy, projectBundle }: any) {
  const plan = production?.production_plan;
  const workflow = plan?.workflow || [];
  const map = plan?.music_map || {};
  const master = production?.master || {};
  return <section className="surface panel production-page">
    <div className="production-hero"><div><span className="kicker">SONG PRODUCTION ENGINE · 11.0</span><h2>From demo to production decision.</h2><p>One transaction connects audio evidence, music mapping, Artist DNA, Song Director, mastering and QC. It does not replace the artist or engineer; it keeps every stage connected.</p></div><div className="production-hero-actions"><button className="button primary" disabled={busy} onClick={run}><Zap size={14}/>{busy ? "BUILDING…" : production ? "RUN AGAIN" : "BUILD PRODUCTION"}</button>{production && <button className="button secondary" disabled={projectBusy} onClick={finalize}><Package size={14}/>{projectBusy ? "PACKAGING…" : "FINALIZE PROJECT"}</button>}</div></div>
    {!production ? <div className="empty production-empty"><Zap size={22}/><p>Load a demo, describe what you want the song to become, then run the production engine.</p></div> : <>
      <div className="production-metrics"><div><span>BPM</span><b>{map.bpm ? num(map.bpm,1) : "—"}</b><small>{map.bpm_confidence != null ? `${num(map.bpm_confidence,0)}% confidence` : "estimate"}</small></div><div><span>KEY</span><b>{map.key || "—"}</b><small>{map.key_confidence != null ? `${num(map.key_confidence,0)}% confidence` : "estimate"}</small></div><div><span>PHRASES</span><b>{map.melody_phrase_count ?? "—"}</b><small>vocal timing candidates</small></div><div><span>MASTER QC</span><b>{master.selected_candidate?.score != null ? num(master.selected_candidate.score,1) : "—"}</b><small>{master.rollback ? "rollback" : "accepted"}</small></div></div>
      <div className="production-flow">{workflow.map((x:any,i:number)=><div key={i} className={x.status === "accepted" || x.status === "complete" ? "done" : ""}><small>{String(i+1).padStart(2,"0")}</small><b>{x.stage}</b><span>{x.detail}</span></div>)}</div>
      <div className="production-grid"><div><span className="kicker">DIRECTOR OUTPUT</span><pre>{production.director?.answer || "No director output."}</pre></div><div><span className="kicker">NEXT ACTIONS</span><ul>{(plan.next_actions||[]).map((x:string,i:number)=><li key={i}>{x}</li>)}</ul>{masterUrl && !master.rollback && <a className="download" href={masterUrl} download><Download size={14}/> DOWNLOAD MASTER WAV</a>} {production.report_url && <a className="download" href={`${API}${production.report_url}`} download><Download size={14}/> DOWNLOAD PRODUCTION REPORT</a>} {projectBundle && <a className="download" href={projectBundle} download><Package size={14}/> DOWNLOAD FINAL PROJECT ZIP</a>}</div></div>
    </>}
  </section>;
}
function MasterPage({ master, profileCfg, runMaster, busy, masterUrl, masterAnalysis, candidateRows }: any) { return <><section className="surface panel master-page"><div className="master-page-top"><div><span className="kicker">MASTER ENGINE</span><h2>Evidence before loudness.</h2><p>Candidate search, corrective processing, final loudness and quality control happen as one transaction. If the result is worse, the original survives.</p></div><button className="button primary" disabled={busy} onClick={runMaster}>{busy ? "PROCESSING" : master ? "RUN AGAIN" : "AUTO MASTER"}</button></div>{master ? <><div className="before-after"><MetricCompare label="LUFS" before={master.analysis?.adaptive_analysis?.lufs} after={masterAnalysis.lufs}/><MetricCompare label="TRUE PEAK" before={master.analysis?.adaptive_analysis?.true_peak_dbfs} after={masterAnalysis.true_peak_dbfs} suffix=" dBTP"/><MetricCompare label="CREST" before={master.analysis?.adaptive_analysis?.crest_factor_db} after={masterAnalysis.crest_factor_db} suffix=" dB"/><MetricCompare label="CORR" before={master.analysis?.adaptive_analysis?.mono_correlation} after={masterAnalysis.mono_correlation}/></div><div className="candidate-table"><div className="candidate-head"><span>CANDIDATE</span><span>FACTOR</span><span>SCORE</span><span>VERDICT</span></div>{candidateRows.map((c:any,i:number)=><div className={`candidate-row ${c.name === master.selected_candidate?.name ? "chosen" : ""}`} key={i}><b>{c.name}</b><span>{num(c.factor,2)}</span><span>{num(c.score,1)}</span><span>{c.verdict}</span>{c.name === master.selected_candidate?.name && <Check size={14}/>}</div>)}</div>{masterUrl && !master.rollback && <a className="download" href={masterUrl} download><Download size={14}/> DOWNLOAD MASTER WAV</a>}</> : <div className="empty master-empty-large"><div className="target-ring"><span>{profileCfg.target}</span><small>LUFS TARGET</small></div><p>Run Auto Master from any screen. The engine will evaluate multiple processing intensities and keep only an acceptable result.</p></div>}</section></>; }
function MetricCompare({ label, before, after, suffix="" }: any) { return <div className="compare"><span>{label}</span><div><b>{num(before,2)}{suffix}</b><ChevronRight size={13}/><b>{num(after,2)}{suffix}</b></div><small>before → after</small></div>; }
function VocalPage({ vocal }: any) { return <section className="surface panel"><PanelHead kicker="VOCAL INTELLIGENCE" title="Pitch & vocal behavior" icon={<Mic2 size={16}/>}/>{vocal && vocal.status !== "no_audio" && vocal.status !== "no_confident_pitch" ? <div className="vocal-grid">{[["RANGE",`${vocal.range_semitones} st`],["LOWEST",vocal.lowest_note],["MEDIAN",vocal.median_note],["HIGHEST",vocal.highest_note],["PITCH ACCURACY",`${vocal.pitch_accuracy_percent}%`],["STABILITY",`${vocal.pitch_stability_percent}%`],["VOICED FRAMES",`${vocal.voiced_ratio}%`],["LEVEL",`${vocal.rms_dbfs} dBFS`]].map(([k,v])=><div key={k}><span>{k}</span><b>{v}</b></div>)}</div> : <Empty icon={<Mic2 size={20}/>} text={vocal?.status === "no_confident_pitch" ? "No confident monophonic pitch detected in the full mix." : "Load a track to run Vocal Intelligence."}/>}<p className="method-note">Pitch is estimated from the full mix. This is not isolated-vocal transcription.</p></section>; }
function StemsPage({ file, stems, busy, runStems }: any) { return <section className="surface panel"><PanelHead kicker="STEM LAB" title="Local GPU separation" icon={<Layers3 size={16}/>}/><div className="feature-intro"><div className="feature-number">01</div><div><b>Demucs · htdemucs</b><p>Separate vocals, drums, bass and other with the local CUDA service. No upload to a remote stem provider.</p></div></div><button className="button primary" disabled={!file || busy} onClick={runStems}><RefreshCw size={14} className={busy ? "spin" : ""}/>{busy ? "SEPARATING ON GPU" : "SEPARATE STEMS"}</button>{stems && <div className="stem-grid">{Object.entries(stems).map(([name,url])=><a key={name} href={`${API}${url}`} target="_blank" rel="noreferrer"><Headphones size={14}/><span>{name.replace(".wav", "")}</span><Download size={13}/></a>)}</div>}</section>; }
function ReferencePage({ reference, master, refRef }: any) { const ref=reference?.adaptive_analysis; const report=master?.reference; return <><section className="surface panel"><PanelHead kicker="REFERENCE" title="Match the intention, not the waveform" icon={<Library size={16}/>}/><p className="lead">Load a finished track as a reference. The engine compares loudness, dynamics, stereo and spectral balance, then keeps the information visible during mastering.</p><button className="button secondary" onClick={()=>refRef.current?.click()}><Upload size={14}/>{reference ? "REPLACE REFERENCE" : "ADD REFERENCE"}</button>{reference && <div className="reference-file"><FileAudio size={15}/><div><b>{reference.file}</b><span>{num(ref?.lufs,1)} LUFS · crest {num(ref?.crest_factor_db,1)} dB · correlation {num(ref?.mono_correlation,2)}</span></div></div>}</section><section className="surface panel section-gap"><PanelHead kicker="COMPARISON" title="Reference delta" icon={<BarChart3 size={16}/>}/>{report && !report.error ? <div className="reference-grid">{[["LUFS DELTA",report.lufs_delta],["CREST DELTA",`${report.crest_delta} dB`],["STEREO WIDTH",`${report.stereo_width_delta} dB`]].map(([k,v])=><div key={k}><span>{k}</span><b>{v}</b></div>)}</div> : <Empty icon={<Library size={20}/>} text={reference ? "Run Auto Master to populate the master-to-reference delta." : "Add a reference track first."}/>}</section></>; }
