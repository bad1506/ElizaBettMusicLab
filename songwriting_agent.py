from __future__ import annotations
import json, os, urllib.error, urllib.request
import songwriter_memory
from datetime import datetime, timezone

AGENT_VERSION = "1.6"

CRAFT_SYSTEM = r"""
Ты — ELIZA BETT SONGWRITER, отдельный AI-агент внутри Eliza Bett Music Lab.
Твоя задача — быть соавтором песни: идея, тема, концепт, hook, припев, куплеты, bridge, рифмы, prosody, структура, редактирование и проверка оригинальности.

ПРИНЦИПЫ:
- Пиши естественно по-русски, современно и певуче.
- Сначала смысл и сильный hook, потом рифма.
- Избегай клише, канцелярита, пустых метафор и одинаковых рифм.
- Используй конкретные детали, действие, образ, внутренний конфликт и разговорную правду.
- Припев должен быть простым для запоминания и иметь одну центральную фразу.
- Куплет должен развивать историю, а не повторять припев другими словами.
- Следи за длиной строк, ударениями, гласными и удобством пения.
- Не копируй тексты существующих песен и не имитируй живого автора. Можно анализировать высокоуровневые приёмы жанра.
- Если пользователь дал свой текст — сохраняй его сильные строки, исправляя только то, что действительно мешает.
- Давай несколько вариантов, когда задача творческая: безопасный, смелый и экспериментальный.
- Для TikTok/short-form учитывай hook в первые строки, но не превращай всю песню в рекламный слоган.
- Для полноценного текста используй рабочую структуру: IDEA → HOOK → CHORUS → VERSE → BRIDGE → FINAL CHORUS.
- Не считай песню законченной только потому, что есть рифмы: проверяй развитие мысли, контраст секций и singability.
- Если пользователь просит полный текст, делай рабочий draft, который можно редактировать построчно.

РЕЖИМЫ:
IDEA — 10 концептов с hook и эмоциональным конфликтом.
HOOK — 10 коротких центральных фраз.
CHORUS — 3 разных припева.
SONG — полноценный черновик с [INTRO], [VERSE], [PRE-CHORUS], [CHORUS], [VERSE 2], [BRIDGE], [FINAL CHORUS].
EDIT — редактура текста построчно.
RHYME — рифмы, созвучия, внутренние рифмы.
PROSODY — проверка ударений и длины строк.
TREND — анализ актуальных сигналов и перевод их в творческие направления без копирования конкретных песен.
"""

TREND_QUERIES = [
    "2026 music trends Russian pop TikTok songwriting hooks lyrics", 
    "2026 Spotify songwriters to watch trends pop R&B hip hop songwriting",
    "2026 TikTok music trends breakout songs songwriting chorus hooks",
]

def _openai(payload, timeout=90):
    key=os.getenv("OPENAI_API_KEY")
    if not key: return None
    body=json.dumps(payload, ensure_ascii=False).encode()
    req=urllib.request.Request("https://api.openai.com/v1/responses", data=body, method="POST", headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data=json.loads(r.read().decode())
        if data.get("output_text"): return data["output_text"].strip()
        out=[]
        for item in data.get("output",[]):
            for part in item.get("content",[]):
                if part.get("text"): out.append(part["text"])
        return "\n".join(out).strip() or None
    except Exception as e:
        print("Songwriter OpenAI error:", e)
        return None

def generate(request: str, mode: str="SONG", context: dict|None=None, trend_context: str=""):
    mode=mode.upper().strip()
    context=context or {}
    artist_dna = songwriter_memory.dna()
    recent_songs = songwriter_memory.recent(6)
    prompt=f"""РЕЖИМ: {mode}\nЗАПРОС АВТОРА:\n{request}\n\nКОНТЕКСТ ПРОЕКТА:\n{json.dumps(context,ensure_ascii=False,indent=2,default=str)}\n\nARTIST DNA — ПАМЯТЬ АВТОРА:\n{json.dumps(artist_dna,ensure_ascii=False,indent=2,default=str)}\n\nПОСЛЕДНИЕ СОХРАНЁННЫЕ ЧЕРНОВИКИ:\n{json.dumps([{'title':x.get('title'),'mode':x.get('mode'),'text':x.get('text','')[:2500]} for x in recent_songs],ensure_ascii=False,indent=2)}\n\nАКТУАЛЬНЫЕ СИГНАЛЫ:\n{trend_context or 'Нет свежего trend context. Не выдумывай тренды.'}\n\nИспользуй Artist DNA как предпочтения, а не как клетку. Не повторяй прошлые строки дословно. Сначала сохраняй авторский голос, затем добавляй новое. Если пишешь текст, маркируй секции и не добавляй пояснения внутрь текста."""
    payload={"model":os.getenv("OPENAI_MODEL","gpt-5.6"),"input":[{"role":"system","content":[{"type":"input_text","text":CRAFT_SYSTEM}]},{"role":"user","content":[{"type":"input_text","text":prompt}]}]}
    return _openai(payload) or fallback(request,mode)

def trend_report(extra: str=""):
    q="""Сделай актуальный music trend report на 2026 год для автора русскоязычной поп/hip-hop/R&B музыки. Исследуй свежие сигналы Spotify for Artists, Spotify editorial/discovery, TikTok/short-form music culture, новости AI music и заметные songwriting patterns. Не копируй тексты. Нужны: 1) темы, 2) hook/chorus patterns, 3) song structures, 4) production-to-lyric implications, 5) что уже перенасыщено, 6) 10 идей, которые можно использовать без копирования. Для каждого важного факта укажи источник и дату. Отделяй факты от inference."""
    if extra: q += "\nДополнительный фокус: "+extra
    payload={"model":os.getenv("OPENAI_MODEL","gpt-5.6"),"tools":[{"type":"web_search"}],"input":[{"role":"system","content":[{"type":"input_text","text":"Ты music trend researcher. Используй веб-поиск. Не выдавай неподтвержденное за факт. Ссылки и даты сохраняй."}]},{"role":"user","content":[{"type":"input_text","text":q}]}]}
    result=_openai(payload,120)
    if result: return {"ok":True,"generated_at":datetime.now(timezone.utc).isoformat(),"report":result}
    return {"ok":False,"generated_at":datetime.now(timezone.utc).isoformat(),"report":"OPENAI_API_KEY не настроен. Trend Agent работает только при доступе к web search через OpenAI Responses API."}

def fallback(request,mode):
    seed=request.strip() or "любовь после расставания"
    if mode=="IDEA":
        return "1. Неожиданный взгляд на тему: «"+seed+"»\nHook: одна фраза, которую герой повторяет себе после события.\n\n2. Контраст: внешне всё нормально, внутри — другое.\nHook: «Я улыбаюсь, чтобы никто не спросил почему».\n\n3. История через одну конкретную деталь.\nHook: предмет/место становится символом отношений."
    if mode=="HOOK": return "1. Я придумал тебе конец, но не придумал себя без тебя.\n2. Всё, что болело вчера, сегодня звучит тише.\n3. Мы были правы друг для друга — просто не вовремя.\n4. Я отпустил тебя, но город помнит твой адрес.\n5. Проблемы только в голове — пока мы делаем их реальней нас."
    if mode=="CHORUS": return "[CHORUS]\nЯ снова накрутил себе кино,\nгде всё должно закончиться плохо.\nНо если отпустить это кино —\nостанется обычная дорога.\nИ, может, всё не так сложно,\nкак я придумал ночью в голове.\nПроблемы только в голове,\nа значит — их можно решить."
    return f"[VERSE]\nЯ записал одну мысль о теме «{seed}».\nНо прежде чем дописывать песню, выберем угол: история, исповедь, диалог или образ.\n\n[CHORUS]\nНужен центральный hook — одна фраза, которую хочется повторить после первого прослушивания."
