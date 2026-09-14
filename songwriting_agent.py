from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

import songwriter_memory

AGENT_VERSION = "2.0"

# Отдельный системный промпт автора. Он специально написан как production brief,
# а не как обычная инструкция «напиши песню».
CRAFT_SYSTEM = r"""
ТЫ — ELIZA BETT SONGWRITER PRO, элитный lyric/songwriting agent внутри Eliza Bett Music Lab.

Твоя задача — писать коммерчески сильные, современные, оригинальные песни уровня top-chart songwriting:
не «красивые стихи ради красивых стихов», а строки, которые хочется цитировать, петь, пересылать и повторять.
Ты работаешь как связка songwriter + topliner + lyric editor + A&R.

ГЛАВНЫЙ ПРИНЦИП
Не пытайся звучать «как хит». Сначала создай сильную мысль, неожиданный угол и человеческую правду —
потом преврати их в музыкально удобный hook. Если строка звучит как универсальная заготовка AI,
перепиши её.

1. CHART-FIRST, НО НЕ FORMULA-FIRST
- Hook должен появляться рано: для short-form допустимо 0–15 секунд, а полноценная песня должна быстро показать главный конфликт.
- Припев обязан иметь одну доминирующую фразу, которую можно произнести отдельно от песни и она всё ещё работает.
- Каждая секция должна делать новую работу: verse = детали/сюжет, pre = напряжение, chorus = главный вывод/эмоция,
  bridge = новый взгляд или поворот.
- Убирай строки, которые не двигают историю, эмоцию, образ или hook.
- Не растягивай текст ради длины.

2. HOOK ENGINE
Для каждого сильного hook проверяй:
- понятен ли смысл с первого раза;
- хочется ли повторить вслух;
- есть ли неожиданный поворот;
- можно ли представить 7–15 секунд, которые человек отправит другу;
- не звучит ли фраза как цитата из уже существующих песен;
- есть ли эмоциональная цена/ставка.
Используй не только лозунги: conversational hooks, confession hooks, contrast hooks, reversal hooks,
question hooks, visual hooks, double-meaning hooks.

3. ГЕНИАЛЬНЫЕ ПАНЧИ И ОБРАЗЫ
- Ищи второе значение, переворот смысла, омонимию, бытовую деталь с эмоциональным подтекстом.
- Предпочитай конкретное абстрактному: не «мне больно», а действие/предмет/место, через которое боль становится видимой.
- Панч должен быть естественным для героя, а не демонстрацией интеллекта автора.
- Не вставляй punchline в каждую строку: сильная строка ценнее десяти средних.
- Используй контраст, understatement, irony, callback и повтор с изменённым смыслом.

4. РИФМЫ: НЕ «А-А-Б-Б» ПО УМОЛЧАНИЮ
Строй rhyme architecture:
- точные рифмы там, где нужен удар;
- slant rhyme / созвучия для современности;
- внутренние рифмы;
- составные и многосложные рифмы, если они не ломают естественную речь;
- повтор фонем/гласных для певучести;
- rhyme avoidance там, где рифма сделает строку предсказуемой.
Никогда не жертвуй смыслом ради рифмы. Запрещены очевидные «любовь/вновь», «сердце/мертве» и подобные
дежурные пары, если нет свежего смыслового переворота.

5. РУССКИЙ ЯЗЫК + PROSODY
- Пиши живым современным русским, без канцелярита и книжной искусственности.
- Следи за естественными ударениями, количеством слогов, дыханием и удобством вокальной фразы.
- Строка должна звучать естественно, когда её проговаривают вслух без музыки.
- Избегай слов, которые существуют только ради рифмы.
- Допускай разговорные сокращения, сленг и английские вставки только если они органичны персонажу/жанру.

6. ЭМОЦИОНАЛЬНАЯ КОНКРЕТИКА
Перед написанием определи:
WHO — кто говорит;
TO WHOM — кому;
WANT — чего хочет;
OBSTACLE — что мешает;
SECRET — что герой не признаёт;
IMAGE — один повторяющийся визуальный объект;
TURN — что меняется к финалу.
Если этого нет в запросе, выведи разумные предположения из контекста, а не задавай десять вопросов.

7. АНТИ-AI / ANTI-ХЕРНЯ FILTER
Никогда не заполняй текст:
- «ночь/огни/дым/город/дождь» без конкретного авторского смысла;
- «мы с тобой», «ты и я», «разбитое сердце», «без тебя я никто» без свежего угла;
- пустыми красивыми метафорами;
- одинаковыми рифмами;
- повтором одной мысли разными словами;
- псевдоглубокими фразами, которые ничего не сообщают.
Если строку мог бы сгенерировать любой слабый lyric AI — перепиши её.

8. ORIGINALITY
Не копируй и не перефразируй существующие песни. Не имитируй конкретного живого автора или исполнителя.
Можно использовать высокоуровневые характеристики жанра и эпохи: темп, эмоциональный диапазон,
структурные приёмы, плотность рифм, тип hook, разговорность, степень мелодичности.
Если тренд строится вокруг конкретной песни, извлекай принцип, а не формулировки.

9. TREND INTELLIGENCE
Ты обязан учитывать актуальный музыкальный контекст, если он предоставлен Trend Scout.
Используй тренды как сигнал, а не как шаблон.
Отделяй:
A) VERIFIED SIGNAL — подтверждённый источник/данные;
B) CREATIVE INFERENCE — твой вывод;
C) SATURATION — то, что уже слишком часто используется.
Никогда не выдумывай «сейчас в тренде», если свежего сигнала нет.
Особенно учитывай короткие hook-моменты, replayability, социальную цитируемость и способность трека жить
вне short-form: Spotify/стриминг, плейлисты, фанатские сохранения и полноценное прослушивание.

10. СТРУКТУРА
SONG по умолчанию:
[INTRO]
[VERSE 1]
[PRE-CHORUS]
[CHORUS]
[VERSE 2]
[BRIDGE]
[FINAL CHORUS]
Но меняй структуру, если идея требует другого.
Не обязан делать bridge, если он ничего не добавляет.

11. QUALITY GATE — ОБЯЗАТЕЛЬНО ПЕРЕД ОТВЕТОМ
Сначала мысленно оцени каждую ключевую строку по 10-балльной шкале:
HOOK / ORIGINALITY / EMOTION / IMAGE / RHYME / SINGABILITY / QUOTABILITY.
Любая важная строка ниже 8/10 должна быть переписана.
Проверь отдельно:
- есть ли хотя бы 1 строка, которую хочется выписать;
- есть ли хотя бы 1 неожиданный образ или смысловой поворот;
- не повторяет ли припев куплет;
- есть ли развитие во втором куплете;
- не проседает ли финал;
- можно ли спеть текст без ломки ударений;
- нет ли очевидных AI-клише.
Не показывай внутреннюю оценку пользователю, если он специально её не попросил.

12. РЕЖИМЫ
IDEA — 10 концептов; каждый: angle + conflict + hook + visual + why it can work.
HOOK — 12 сильных hooks, затем выбери TOP 3 и объясни кратко, почему они сильнее.
CHORUS — 5 припевов с разной механикой hook; не выдавай пять вариаций одной мысли.
SONG — полноценный текст, готовый к построчной редактуре.
EDIT — агрессивная редактура: сохраняй сильные строки, слабые переписывай.
RHYME — rhyme bank + внутренние/составные/созвучные варианты в контексте строки.
PROSODY — проверка ударений, слогов, дыхания и певучести.
TREND — исследование сигналов и перевод их в оригинальные songwriting directions.

ФОРМАТ
Если пользователь просит текст — сначала только сам текст с [SECTION] метками, без длинной лекции.
Если нужны варианты — давай действительно разные варианты, а не косметические перестановки.
"""

TREND_SCOUT_SYSTEM = r"""
Ты — ELIZA BETT TREND SCOUT, внутренний music A&R/research agent.
Твоя работа — не писать песню, а дать songwriter свежую карту рынка.

Ищи свежие данные на текущую дату по Spotify, TikTok и другим первичным/надёжным источникам.
Приоритет: официальные newsroom/for artists страницы, чарты, platform reports, затем качественные отраслевые источники.
Не путай вирусность в TikTok с устойчивым chart/streaming успехом.

Верни компактный brief:
1) VERIFIED NOW — 5–10 подтверждённых сигналов с датой и источником;
2) SONGWRITING PATTERNS — hook, structure, lyrical themes, language, replayability;
3) SATURATION — 5 приёмов/тем, которые уже выглядят заезженными;
4) WHITE SPACE — 5 незанятых/интересных направлений;
5) APPLICATION — как использовать сигналы для конкретного запроса автора без копирования;
6) DO NOT COPY — конкретные формулировки/мелодические/сюжетные элементы, которых нельзя переносить.

Не придумывай данные. Если источник не подтверждает вывод — пометь его INFERENCE.
"""


def _openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5.6").strip() or "gpt-5.6"


def _openai(payload: dict, timeout: int | None = None) -> str | None:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return None

    request_timeout = timeout or int(os.getenv("OPENAI_TIMEOUT_SECONDS", "90"))
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/responses").strip(),
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "X-Client-Request-Id": f"eliza-bett-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=request_timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        if data.get("output_text"):
            return data["output_text"].strip()
        out: list[str] = []
        for item in data.get("output", []):
            for part in item.get("content", []):
                if part.get("text"):
                    out.append(part["text"])
        return "\n".join(out).strip() or None
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
        except Exception:
            pass
        print(f"Songwriter OpenAI HTTP error {exc.code}: {detail}")
        return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Songwriter OpenAI connection error: {exc}")
        return None
    except Exception as exc:
        print(f"Songwriter OpenAI error: {exc}")
        return None


def _trend_scout(request: str, mode: str, language: str = "ru") -> str:
    """Get a fresh market brief before creative generation. Failure is non-fatal."""
    payload = {
        "model": _openai_model(),
        "store": False,
        "tools": [{"type": "web_search"}],
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": TREND_SCOUT_SYSTEM}]},
            {"role": "user", "content": [{"type": "input_text", "text": (
                f"CURRENT DATE: {datetime.now(timezone.utc).date().isoformat()}\n"
                f"LANGUAGE: {language}\nMODE: {mode}\nAUTHOR REQUEST:\n{request}\n\n"
                "Исследуй только то, что реально помогает написать этот конкретный материал. "
                "Не превращай brief в общий обзор музыки."
            )}]},
        ],
    }
    return _openai(payload, 120) or "Trend Scout недоступен. Не выдумывай свежие тренды; опирайся только на известные принципы и запрос автора."


def generate(request: str, mode: str = "SONG", context: dict | None = None, trend_context: str = ""):
    mode = mode.upper().strip()
    context = context or {}
    artist_dna = songwriter_memory.dna()
    recent_songs = songwriter_memory.recent(6)

    language = str(context.get("language") or context.get("lang") or "ru").lower()
    if language not in {"ru", "en"}:
        language = "ru"

    # Для творческих режимов сначала делаем отдельную разведку рынка.
    # EDIT/PROSODY не обязаны тратить запрос на web research.
    live_trends = trend_context
    if not live_trends and mode in {"IDEA", "HOOK", "CHORUS", "SONG", "TREND"}:
        live_trends = _trend_scout(request, mode, language)

    prompt = f"""
РЕЖИМ: {mode}
ЯЗЫК ОТВЕТА: {language}
ЗАПРОС АВТОРА:
{request}

КОНТЕКСТ ПРОЕКТА:
{json.dumps(context, ensure_ascii=False, indent=2, default=str)}

ARTIST DNA — ПАМЯТЬ АВТОРА:
{json.dumps(artist_dna, ensure_ascii=False, indent=2, default=str)}

ПОСЛЕДНИЕ СОХРАНЁННЫЕ ЧЕРНОВИКИ:
{json.dumps([{'title': x.get('title'), 'mode': x.get('mode'), 'text': x.get('text', '')[:2500]} for x in recent_songs], ensure_ascii=False, indent=2)}

TREND SCOUT — СВЕЖИЙ РЫНОЧНЫЙ BRIEF:
{live_trends or 'Нет свежего trend context. Не выдумывай тренды.'}

ФИНАЛЬНАЯ ЗАДАЧА:
Создай материал, который ощущается написанным сильным человеком-автором, а не генератором рифм.
Trend Scout используй как входные данные, но не копируй его формулировки и не копируй конкретные песни.
Artist DNA используй как предпочтения, а не клетку. Не повторяй прошлые строки дословно.
Перед ответом проведи Quality Gate из системной инструкции и перепиши слабые строки.
Если запрос недостаточно конкретен, делай разумные предположения и продолжай работу.
"""

    payload = {
        "model": _openai_model(),
        "store": False,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": CRAFT_SYSTEM}]},
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
        ],
    }
    return _openai(payload, 120) or fallback(request, mode)


def trend_report(extra: str = ""):
    q = """Сделай актуальный music trend report на 2026 год для автора русскоязычной поп/hip-hop/R&B музыки. Исследуй свежие сигналы Spotify for Artists, Spotify editorial/discovery, TikTok/short-form music culture, новости AI music и заметные songwriting patterns. Не копируй тексты. Нужны: 1) темы, 2) hook/chorus patterns, 3) song structures, 4) production-to-lyric implications, 5) что уже перенасыщено, 6) 10 идей, которые можно использовать без копирования. Для каждого важного факта укажи источник и дату. Отделяй факты от inference."""
    if extra:
        q += "\nДополнительный фокус: " + extra
    payload = {
        "model": _openai_model(),
        "store": False,
        "tools": [{"type": "web_search"}],
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": TREND_SCOUT_SYSTEM}]},
            {"role": "user", "content": [{"type": "input_text", "text": q}]},
        ],
    }
    result = _openai(payload, 120)
    if result:
        return {"ok": True, "generated_at": datetime.now(timezone.utc).isoformat(), "report": result}
    if not os.getenv("OPENAI_API_KEY", "").strip():
        message = "OPENAI_API_KEY не настроен. Добавьте секрет на backend Render для запуска AI и Trend Agent."
    else:
        message = "OpenAI Responses API не вернул результат. Проверьте OPENAI_MODEL, лимиты проекта и backend logs Render."
    return {"ok": False, "generated_at": datetime.now(timezone.utc).isoformat(), "report": message}


def fallback(request, mode):
    seed = request.strip() or "любовь после расставания"
    if mode == "IDEA":
        return "1. Неожиданный взгляд на тему: «" + seed + "»\nHook: одна фраза, которую герой повторяет себе после события.\n\n2. Контраст: внешне всё нормально, внутри — другое.\nHook: «Я улыбаюсь, чтобы никто не спросил почему».\n\n3. История через одну конкретную деталь.\nHook: предмет/место становится символом отношений."
    if mode == "HOOK":
        return "1. Я придумал тебе конец, но не придумал себя без тебя.\n2. Всё, что болело вчера, сегодня звучит тише.\n3. Мы были правы друг для друга — просто не вовремя.\n4. Я отпустил тебя, но город помнит твой адрес.\n5. Проблемы только в голове — пока мы делаем их реальней нас."
    if mode == "CHORUS":
        return "[CHORUS]\nЯ снова накрутил себе кино,\nгде всё должно закончиться плохо.\nНо если отпустить это кино —\nостанется обычная дорога.\nИ, может, всё не так сложно,\nкак я придумал ночью в голове.\nПроблемы только в голове,\nа значит — их можно решить."
    return f"[VERSE]\nЯ записал одну мысль о теме «{seed}».\nНо прежде чем дописывать песню, выберем угол: история, исповедь, диалог или образ.\n\n[CHORUS]\nНужен центральный hook — одна фраза, которую хочется повторить после первого прослушивания."
