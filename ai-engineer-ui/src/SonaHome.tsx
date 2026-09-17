import { ArrowRight, ChevronLeft, ChevronRight, Moon, Pause, Play, Sun, Volume2 } from "lucide-react";
import "./SonaHome.css";

type Copy = { start: string; tools: string[]; descriptions: string[]; latest: string; all: string };

type Props = {
  c: Copy;
  go: (page: string) => void;
  openTool: (id: "songwriter" | "analyzer" | "master" | "trends") => void;
};

const legends = [
  { name: "The Weeknd", story: "От анонимности к мировому признанию.", accent: "#b7aaa0" },
  { name: "Rihanna", story: "Сила, свобода и собственный голос.", accent: "#c3b7ac" },
  { name: "Eminem", story: "Путь через боль к мировой сцене.", accent: "#9f9b95" },
  { name: "Billie Eilish", story: "Другая реальность и новый язык поп-музыки.", accent: "#b2aea6" },
  { name: "Kendrick Lamar", story: "Голос поколения и культурный диалог.", accent: "#8f8a84" },
  { name: "Ariana Grande", story: "Музыка как пространство для нового звучания.", accent: "#c1b6aa" },
  { name: "Taylor Swift", story: "Истории, превращённые в музыку.", accent: "#aaa49c" },
  { name: "Travis Scott", story: "Энергия, миры и новая сцена.", accent: "#8d8983" },
  { name: "Drake", story: "Между рэпом, мелодией и личной историей.", accent: "#aaa69f" },
  { name: "Ed Sheeran", story: "Простота, которая стала мировой музыкой.", accent: "#bdb4aa" },
];

const playlists = [
  ["Focus", "Для концентрации", "◐"],
  ["Deep Work", "Работа и идеи", "◒"],
  ["Chill", "Спокойный вечер", "◌"],
  ["Late Night", "Ночная атмосфера", "☾"],
  ["AI Covers", "Эксперименты SØNA", "◇"],
];

const chart = [
  ["Miyagi & Endspiel", "Не жалею"],
  ["The Weeknd", "Popular"],
  ["Billie Eilish", "LUNCH"],
  ["Океан Ельзи", "Обійми"],
  ["Artik & Asti", "Грустный дэнс"],
];

export default function SonaHome({ c, go, openTool }: Props) {
  const [legend, setLegend] = React.useState(0);
  const [playing, setPlaying] = React.useState(false);
  const [playlist, setPlaylist] = React.useState(0);

  const currentLegend = legends[legend];
  const moveLegend = (delta: number) => setLegend((value) => (value + delta + legends.length) % legends.length);

  return (
    <main className="sona-home">
      <section className="sona-hero">
        <div className="sona-hero-copy">
          <span className="sona-eyebrow">AI SONGWRITER · MUSIC INTELLIGENCE</span>
          <h1>Создавай<br /><span>свою музыку</span><br />с SØNA</h1>
          <p>Текст. Идея. Эмоция. Структура. SØNA помогает пройти путь от первой мысли до готового трека.</p>
          <div className="sona-actions">
            <button className="sona-primary" onClick={() => openTool("songwriter")}>Создать текст песни <ArrowRight size={17} /></button>
            <button className="sona-ghost" onClick={() => go("tools")}>Открыть AI Студию</button>
          </div>
          <div className="sona-capabilities">
            <span><b>01</b>Генерация<br />текста</span>
            <span><b>02</b>Стиль<br />и настроение</span>
            <span><b>03</b>Вдохновение<br />из трендов</span>
            <span><b>04</b>Профессиональный<br />результат</span>
          </div>
        </div>
        <div className="sona-atmosphere" aria-hidden="true">
          <div className="sona-moon" />
          <div className="sona-cloud sona-cloud-a" />
          <div className="sona-cloud sona-cloud-b" />
          <div className="sona-mountain sona-mountain-a" />
          <div className="sona-mountain sona-mountain-b" />
        </div>
        <aside className="sona-chart glass-card">
          <div className="card-title"><div><strong>Топ 10</strong><span>Яндекс Музыки</span></div><button aria-label="Открыть чарты" onClick={() => openTool("trends")}><ArrowRight size={16} /></button></div>
          <div className="chart-list">
            {chart.map(([artist, song], index) => (
              <button key={artist} className="chart-row" onClick={() => openTool("trends")}>
                <b>{index + 1}</b><span className={`chart-avatar chart-${index}`}>{artist.slice(0, 1)}</span><span><strong>{artist}</strong><small>{song}</small></span><ChevronRight size={13} />
              </button>
            ))}
          </div>
          <button className="chart-all" onClick={() => openTool("trends")}>Смотреть весь чарт <ArrowRight size={14} /></button>
        </aside>
      </section>

      <section className="sona-playlists glass-card">
        <div className="section-heading"><div><h2>Плейлисты</h2><p>Под любое настроение</p></div><button onClick={() => go("tracks")}>{c.all} <ArrowRight size={15} /></button></div>
        <div className="playlist-track">
          {playlists.map(([title, subtitle, symbol], index) => (
            <button key={title} className={`playlist-card ${playlist === index ? "selected" : ""}`} onClick={() => setPlaylist(index)}>
              <div className={`playlist-art art-${index}`}><span>{symbol}</span></div>
              <strong>{title}</strong><small>{subtitle}</small><i><Play size={12} fill="currentColor" /></i>
            </button>
          ))}
        </div>
      </section>

      <section className="sona-lower">
        <div className="sona-library glass-card">
          <div className="section-heading"><div><h2>Моя музыка</h2><p>Твои проекты в одном месте</p></div><button onClick={() => go("tracks")}>Открыть <ArrowRight size={15} /></button></div>
          <div className="library-stats"><div><b>24</b><span>Трека</span></div><div><b>8</b><span>Избранное</span></div><div><b>12</b><span>Плейлистов</span></div><div><b>6</b><span>Проектов</span></div></div>
        </div>
        <div className="sona-quick glass-card">
          <div className="section-heading"><div><h2>AI Studio</h2><p>Быстрый старт</p></div><button onClick={() => go("tools")}><ArrowRight size={15} /></button></div>
          <div className="quick-grid"><button onClick={() => openTool("songwriter")}><span>✎</span>Текст</button><button onClick={() => openTool("analyzer")}><span>⌁</span>Анализ</button><button onClick={() => openTool("master")}><span>◫</span>Мастеринг</button><button onClick={() => openTool("trends")}><span>◌</span>Тренды</button></div>
        </div>
      </section>

      <section className="sona-legends glass-card">
        <div className="section-heading"><div><span className="sona-eyebrow">STORY MUSIC</span><h2>Истории легенд</h2><p>Узнай, как создавалась музыка, которая изменила мир.</p></div><button onClick={() => go("tracks")}>Все истории <ArrowRight size={15} /></button></div>
        <div className="legend-stage">
          <button className="legend-arrow left" aria-label="Предыдущая история" onClick={() => moveLegend(-1)}><ChevronLeft size={18} /></button>
          <div className="legend-stack">
            {[1, 2, 0].map((offset, i) => {
              const item = legends[(legend + offset) % legends.length];
              return <div key={`${item.name}-${i}`} className={`legend-sheet sheet-${i}`} style={{ "--legend-accent": item.accent } as React.CSSProperties}><div className="legend-portrait"><span>{item.name.slice(0, 1)}</span></div></div>;
            })}
            <div className="legend-story-card glass-card-inner">
              <span className="legend-number">{String(legend + 1).padStart(2, "0")} / 10</span>
              <h3>{currentLegend.name}</h3>
              <p>{currentLegend.story}</p>
              <button onClick={() => go("tracks")}>Читать историю <ArrowRight size={14} /></button>
            </div>
          </div>
          <button className="legend-arrow right" aria-label="Следующая история" onClick={() => moveLegend(1)}><ChevronRight size={18} /></button>
        </div>
      </section>

      <section className="sona-player glass-card">
        <div className="player-track"><div className="player-cover">◌</div><div><strong>Осколки Памяти</strong><small>AETERNA</small></div></div>
        <button className="player-like" aria-label="Добавить в избранное">♡</button>
        <span className="player-time">2:28</span>
        <div className="player-wave">{Array.from({ length: 42 }, (_, i) => <i key={i} style={{ height: `${25 + ((i * 17) % 60)}%` }} />)}</div>
        <button className="player-skip" aria-label="Предыдущий трек"><ChevronLeft size={18} /></button>
        <button className="player-main" aria-label={playing ? "Пауза" : "Воспроизвести"} onClick={() => setPlaying((value) => !value)}>{playing ? <Pause size={21} fill="currentColor" /> : <Play size={21} fill="currentColor" />}</button>
        <button className="player-skip" aria-label="Следующий трек"><ChevronRight size={18} /></button>
        <div className="player-wave player-wave-right">{Array.from({ length: 36 }, (_, i) => <i key={i} style={{ height: `${20 + ((i * 11) % 55)}%` }} />)}</div>
        <span className="player-time">5:33</span><button className="volume" aria-label="Громкость"><Volume2 size={18} /></button><div className="volume-line"><span /></div>
      </section>

      <div className="sona-mobile-theme" aria-hidden="true"><Sun size={15} /><Moon size={15} /></div>
    </main>
  );
}

import React from "react";
export { Sun, Moon };
