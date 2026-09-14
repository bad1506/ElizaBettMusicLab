import { useMemo, useState } from "react";
import { Check, FileText, Lightbulb, PenLine, RotateCcw, Save, Sparkles, Target, Wand2 } from "lucide-react";

type Mode = "IDEA" | "HOOK" | "CHORUS" | "SONG" | "EDIT" | "RHYME" | "PROSODY" | "HIT";

type Draft = { id: string; title: string; text: string; updatedAt: string };

const MODES: Array<{ id: Mode; ru: string; en: string; icon: typeof Sparkles }> = [
  { id: "IDEA", ru: "Идея", en: "Idea", icon: Lightbulb },
  { id: "HOOK", ru: "Хук", en: "Hook", icon: Target },
  { id: "CHORUS", ru: "Припев", en: "Chorus", icon: Sparkles },
  { id: "SONG", ru: "Песня", en: "Song", icon: PenLine },
  { id: "EDIT", ru: "Редактор", en: "Edit", icon: Wand2 },
  { id: "RHYME", ru: "Рифмы", en: "Rhymes", icon: RotateCcw },
  { id: "PROSODY", ru: "Просодия", en: "Prosody", icon: Check },
  { id: "HIT", ru: "Hit Score", en: "Hit Score", icon: Target },
];

function scoreText(text: string) {
  const lines = text.split(/\n+/).map(x => x.trim()).filter(Boolean);
  const words = text.toLowerCase().match(/[a-zа-яё0-9'-]+/gi) || [];
  const unique = new Set(words).size;
  const repetition = words.length ? 1 - unique / words.length : 0;
  const chorus = /\[?chorus\]?/i.test(text);
  const hookLines = lines.slice(0, 4).join(" ");
  const shortHook = hookLines.split(/\s+/).filter(Boolean).length <= 28;
  const cliché = /(разбитое сердце|без тебя я никто|ночь и огни|город не спит|слезы на щеках|дым сигарет|мокрый асфальт)/i.test(text);
  const hook = Math.max(0, Math.min(100, 68 + (chorus ? 12 : 0) + (shortHook ? 10 : 0)));
  const originality = Math.max(0, Math.min(100, 91 - repetition * 35 - (cliché ? 18 : 0)));
  const emotion = Math.max(0, Math.min(100, 52 + Math.min(35, lines.length * 2)));
  const singability = Math.max(0, Math.min(100, 88 - Math.max(0, lines.reduce((a, x) => a + x.length, 0) / Math.max(1, lines.length) - 55) * 0.45));
  const quotability = Math.round(hook * .65 + originality * .35);
  const structure = Math.min(100, 55 + (chorus ? 20 : 0) + (/\[?verse\]?/i.test(text) ? 15 : 0) + (/\[?bridge\]?/i.test(text) ? 10 : 0));
  const total = Math.round(hook * .23 + originality * .19 + emotion * .15 + singability * .15 + quotability * .12 + structure * .10 + Math.max(0, 100 - repetition * 100) * .06);
  return { total, hook: Math.round(hook), originality: Math.round(originality), emotion: Math.round(emotion), singability: Math.round(singability), quotability, structure, cliché };
}

export default function SongwriterStudio({ lang, onGenerate }: { lang: "ru" | "en"; onGenerate: (mode: Mode, prompt: string) => void }) {
  const [mode, setMode] = useState<Mode>("SONG");
  const [draft, setDraft] = useState("");
  const [title, setTitle] = useState(lang === "ru" ? "Новый текст" : "New draft");
  const [drafts, setDrafts] = useState<Draft[]>(() => { try { return JSON.parse(localStorage.getItem("eliza_textbook") || "[]"); } catch { return []; } });
  const score = useMemo(() => scoreText(draft), [draft]);
  const ru = lang === "ru";
  const save = () => { const next = [{ id: crypto.randomUUID(), title: title || (ru ? "Без названия" : "Untitled"), text: draft, updatedAt: new Date().toLocaleString() }, ...drafts].slice(0, 20); setDrafts(next); localStorage.setItem("eliza_textbook", JSON.stringify(next)); };
  const action = (label: string) => onGenerate(mode, `${label}. ${draft ? `Вот текущий текст:\n${draft}` : "Развивай идею с нуля."}`);
  return <div className="songwriter-studio">
    <div className="studio-modebar">{MODES.map(item => { const Icon = item.icon; return <button className={mode === item.id ? "active" : ""} key={item.id} onClick={() => setMode(item.id)}><Icon size={14}/>{ru ? item.ru : item.en}</button>; })}</div>
    <div className="studio-grid">
      <section className="textbook-card">
        <div className="studio-head"><div><span className="eyebrow"><FileText size={12}/> TEXTBOOK</span><h3>{ru ? "Рабочий текст" : "Working text"}</h3></div><button className="save-draft" onClick={save}><Save size={14}/>{ru ? "Сохранить" : "Save"}</button></div>
        <input className="draft-title" value={title} onChange={e => setTitle(e.target.value)} placeholder={ru ? "Название текста" : "Draft title"}/>
        <textarea className="draft-editor" value={draft} onChange={e => setDraft(e.target.value)} placeholder={ru ? "Вставь текст песни или начни с идеи..." : "Paste lyrics or start with an idea..."}/>
        <div className="ai-actions"><button onClick={() => action(ru ? "Усиль текст и сделай строки точнее" : "Strengthen the lyrics and make every line more precise")}> <Wand2 size={14}/> {ru ? "Усилить" : "Strengthen"}</button><button onClick={() => action(ru ? "Дай 10 сильных рифм к ключевым словам" : "Give 10 strong rhymes for the key words")}><Sparkles size={14}/> {ru ? "Рифмы" : "Rhymes"}</button><button onClick={() => action(ru ? "Сделай припев более цепляющим" : "Make the chorus more catchy")}><Target size={14}/> {ru ? "Хук" : "Hook"}</button><button onClick={() => action(ru ? "Перепиши, сохранив смысл и авторский голос" : "Rewrite while preserving meaning and voice")}><PenLine size={14}/> {ru ? "Переписать" : "Rewrite"}</button></div>
      </section>
      <aside className="score-card"><div className="studio-head"><div><span className="eyebrow">QUALITY GATE</span><h3>{ru ? "Hit Score" : "Hit Score"}</h3></div><div className={`score-status ${score.total >= 82 && !score.cliché ? "pass" : "rework"}`}>{score.total >= 82 && !score.cliché ? "PASS" : "REWORK"}</div></div><div className="score-main"><strong>{score.total}</strong><span>/100</span></div>{[[ru?"Hook":"Hook",score.hook],[ru?"Originality":"Originality",score.originality],[ru?"Emotion":"Emotion",score.emotion],[ru?"Singability":"Singability",score.singability],[ru?"Quotability":"Quotability",score.quotability],[ru?"Structure":"Structure",score.structure]].map(([label,value])=><div className="score-row" key={String(label)}><span>{label}</span><b>{value}</b><i><em style={{width:`${value}%`}}/></i></div>)}<p className="score-note">{score.cliché ? (ru ? "Найдены типовые клише — перепиши hook и конкретизируй образы." : "Common clichés detected — rewrite the hook and make imagery more specific.") : score.total >= 82 ? (ru ? "Текст проходит базовый editorial gate. Проверь его на реальной мелодии." : "The draft passes the basic editorial gate. Check it against the real topline.") : (ru ? "Сначала усили слабое место, затем запусти оценку снова." : "Strengthen the weakest area, then run the score again.")}</p></aside>
    </div>
    <div className="textbook-saved"><div className="studio-head"><h3>{ru ? "Сохранённые черновики" : "Saved drafts"}</h3><span>{drafts.length}/20</span></div>{drafts.length ? <div className="saved-list">{drafts.slice(0, 5).map(d => <button key={d.id} onClick={() => {setTitle(d.title);setDraft(d.text);}}><b>{d.title}</b><small>{d.updatedAt}</small></button>)}</div> : <p>{ru ? "Сохраняй тексты здесь — они останутся в этом браузере." : "Save drafts here — they stay in this browser."}</p>}</div>
  </div>;
}
