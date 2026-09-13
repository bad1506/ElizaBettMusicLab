from __future__ import annotations
import re

VOWELS = set("аеёиоуыэюяaeiouy")


def _lines(text):
    return [x.strip() for x in text.splitlines() if x.strip()]


def _syllables(line):
    return sum(1 for ch in line.lower() if ch in VOWELS)


def _sections(text):
    out=[]; current="TEXT"
    for raw in text.splitlines():
        m=re.match(r"\s*\[(INTRO|VERSE|PRE-CHORUS|CHORUS|BRIDGE|FINAL CHORUS|OUTRO)\]\s*", raw, re.I)
        if m: current=m.group(1).upper(); continue
        if raw.strip(): out.append((current, raw.strip()))
    return out


def analyze(text: str):
    lines=_lines(text)
    sec=_sections(text)
    words=re.findall(r"[A-Za-zА-Яа-яЁё0-9'-]+", text.lower())
    unique=len(set(words)); total=len(words)
    repeated=max(0,total-unique)
    avg=sum(len(x.split()) for x in lines)/len(lines) if lines else 0
    syll=[_syllables(x) for x in lines]
    spread=(max(syll)-min(syll)) if syll else 0
    chorus=[x for s,x in sec if s in {"CHORUS","FINAL CHORUS"}]
    hook=chorus[0] if chorus else (lines[0] if lines else "")
    # Heuristic scores are editorial aids, not linguistic truth.
    memorability=max(0,min(100, 48 + (18 if chorus else 0) + (12 if len(hook.split())<=9 else 0) + (8 if repeated else 0)))
    variety=max(0,min(100, 100 - (repeated/total*100 if total else 0)))
    singability=max(0,min(100, 92 - spread*4 - max(0,avg-11)*2))
    structure=[s for s,_ in sec]
    expected=["VERSE","CHORUS"]
    structure_score=70 if any(x=="CHORUS" for x in structure) else 35
    if "VERSE" in structure and "CHORUS" in structure: structure_score+=15
    if "BRIDGE" in structure: structure_score+=10
    return {
        "line_count":len(lines), "word_count":total, "unique_words":unique,
        "repetition_percent":round(repeated/total*100,1) if total else 0,
        "average_words_per_line":round(avg,1), "syllable_range":spread,
        "hook":hook[:180], "sections":structure,
        "scores":{"hook_memorability":round(memorability),"word_variety":round(variety),"singability":round(singability),"structure":min(100,structure_score)},
        "notes":[
            "Эвристическая проверка: ударения и рифмы не распознаются как профессиональный вокальный редактор.",
            "Проверь строки с большим разбросом слогов на мелодии.",
            "Если припев есть, протестируй центральную фразу отдельно без контекста куплета."
        ]
    }
