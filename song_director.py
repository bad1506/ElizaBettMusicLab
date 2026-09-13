from __future__ import annotations
import json, os, urllib.request
from datetime import datetime, timezone
import songwriter_memory

VERSION = "6.9"

SYSTEM = r"""
Ты — ELIZA BETT AI SONG DIRECTOR 6.9. Ты управляешь творческим предпродакшеном песни.
Получаешь аудио-анализ, BPM, предполагаемую тональность, beat map, кандидатные секции, vocal activity, вокальные метрики, Artist DNA, пользовательский brief и актуальные trend signals.
Твоя задача — не просто написать текст, а создать coherent creative brief:
1) creative concept, 2) emotional conflict, 3) hook, 4) song structure, 5) lyric density,
6) vocal delivery direction, 7) production direction, 8) melody/lyric alignment, 9) short-form moment, 9) full lyric draft,
10) Suno-ready prompt, 11) risks and revision plan.
Дополнительно проектируй lyric density и фразировку относительно реальной длительности/секции демо. Используй melody_map как timing evidence: phrase duration, gaps и estimated syllable budget. Не называй эвристический syllable budget фактическим количеством слогов.

ПРАВИЛА:
- Авторский голос важнее тренда.
- Тренд — сигнал, не шаблон.
- Не копируй строки, мелодии или узнаваемые особенности конкретных живых артистов.
- Можно использовать высокоуровневые жанровые и композиционные приёмы.
- Если BPM/тональность/вокал не определены, не выдумывай точные значения; помечай как estimate/unknown.
- Если аудио недостаточно для вывода, скажи что именно неизвестно.
- Hook должен быть конкретным и пригодным для повторения.
- Куплет развивает конфликт, припев меняет эмоциональную высоту.
- Сначала идея и структура, потом полный текст.
- Разделяй факты, inference и creative proposal.
- Не обещай вирусность.
"""


def _openai(payload, timeout=120):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    body = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses", data=body, method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        if data.get("output_text"):
            return data["output_text"].strip()
        out=[]
        for item in data.get("output",[]):
            for part in item.get("content",[]):
                if part.get("text"): out.append(part["text"])
        return "\n".join(out).strip() or None
    except Exception as e:
        print("Song Director error:", e)
        return None


def _fallback(request, context, trend_context):
    a = context.get("analysis") or {}
    vocal = context.get("vocal") or {}
    dna = songwriter_memory.dna()
    title = context.get("track") or "Новая песня"
    bpm = context.get("bpm") or "не определён"
    lufs = a.get("lufs", "—")
    corr = a.get("mono_correlation", "—")
    themes = ", ".join((dna.get("themes") or [])[:4]) or "личная история, внутренний конфликт"
    return f"""AI SONG DIRECTOR · {title}\n\nCONCEPT\n{request or 'Песня о внутреннем конфликте, который меняется через конкретную деталь.'}\n\nSIGNALS\nBPM: {bpm}\nLUFS: {lufs}\nStereo correlation: {corr}\nVocal range estimate: {vocal.get('range','не определён')}\nArtist DNA themes: {themes}\n\nCREATIVE DIRECTION\nСделать песню личной, конкретной и разговорной. Не гнаться за трендом напрямую; использовать актуальный короткий hook как вход в историю.\n\nHOOK\n«Я придумал проблему раньше, чем она случилась».\n\nSTRUCTURE\n[INTRO] 1–2 строки → [VERSE] конкретная сцена → [PRE-CHORUS] наращивание → [CHORUS] главный hook → [VERSE 2] последствия → [BRIDGE] смена взгляда → [FINAL CHORUS] новый смысл hook.\n\nLYRIC DENSITY\nКуплеты: средняя плотность. Припев: ниже, больше повторяемости и воздуха.\n\nVOCAL DIRECTION\nКуплет близко к речи; припев шире и эмоциональнее. Не перегружать словами сильные ноты.\n\nSHORT-FORM MOMENT\nПервые 7–12 секунд должны содержать самостоятельную мысль, которую можно понять без контекста.\n\nSUNO-READY DIRECTION\nRussian female vocal, intimate modern pop / pop-rap, restrained verses, emotionally lifting chorus, clear central hook, contemporary drums, clean low end, spacious vocal, memorable short-form opening. Preserve natural conversational phrasing.\n\nREVISION PLAN\n1. Проверить hook без музыки.\n2. Убрать общие слова из куплета.\n3. Проверить ударения на мелодии.\n4. Сравнить финальный припев с первым по смыслу, а не только по словам.\n\nSTATUS\nFallback director: OPENAI_API_KEY не настроен, поэтому AI-генерация полного creative brief недоступна. Измерения и локальный Artist DNA использованы там, где доступны."""


def direct(request: str, context: dict | None = None, trend_context: str = ""):
    context = context or {}
    dna = songwriter_memory.dna()
    recent = songwriter_memory.recent(4)
    prompt = f"""AUTHOR BRIEF:\n{request}\n\nPROJECT CONTEXT:\n{json.dumps(context, ensure_ascii=False, indent=2, default=str)}\n\nARTIST DNA:\n{json.dumps(dna, ensure_ascii=False, indent=2, default=str)}\n\nRECENT DRAFTS (for taste only; do not copy):\n{json.dumps([{'title':x.get('title'),'text':x.get('text','')[:1800]} for x in recent], ensure_ascii=False, indent=2)}\n\nTREND CONTEXT:\n{trend_context or 'No fresh trend report. Do not invent trends.'}\n\nReturn a structured Russian creative brief with these headings exactly:\nCONCEPT\nEVIDENCE / INFERENCE\nHOOK\nSTRUCTURE\nLYRIC DENSITY\nVOCAL DIRECTION\nPRODUCTION DIRECTION\nSHORT-FORM MOMENT\nFULL LYRIC DRAFT\nSUNO-READY PROMPT\nRISKS\nREVISION PLAN\n"""
    payload={"model":os.getenv("OPENAI_MODEL","gpt-5.6"),"input":[
        {"role":"system","content":[{"type":"input_text","text":SYSTEM}]},
        {"role":"user","content":[{"type":"input_text","text":prompt}]}
    ]}
    answer = _openai(payload)
    if answer:
        return {"ok":True,"version":VERSION,"generated_at":datetime.now(timezone.utc).isoformat(),"answer":answer,"mode":"AI"}
    return {"ok":True,"version":VERSION,"generated_at":datetime.now(timezone.utc).isoformat(),"answer":_fallback(request,context,trend_context),"mode":"FALLBACK"}
