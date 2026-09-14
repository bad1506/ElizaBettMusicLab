from __future__ import annotations
import re

VOWELS = set("аеёиоуыэюяaeiouy")
CLICHES = (
    "разбитое сердце", "без тебя я никто", "ночь и огни", "город не спит",
    "слезы на щеках", "мы с тобой", "ты и я", "любовь и вновь", "сердце и мертве",
    "дым сигарет", "мокрый асфальт"
)


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
    structure=[s for s,_ in sec]
    memorability=max(0,min(100, 48 + (18 if chorus else 0) + (12 if len(hook.split())<=9 else 0) + (8 if repeated else 0)))
    variety=max(0,min(100, 100 - (repeated/total*100 if total else 0)))
    singability=max(0,min(100, 92 - spread*4 - max(0,avg-11)*2))
    structure_score=70 if any(x=="CHORUS" for x in structure) else 35
    if "VERSE" in structure and "CHORUS" in structure: structure_score+=15
    if "BRIDGE" in structure: structure_score+=10
    cliché_hits=[]
    lower=text.lower()
    for phrase in CLICHES:
        if phrase in lower: cliché_hits.append(phrase)
    concrete_bonus=min(100, len({w for w in words if len(w)>5}) * 2)
    originality=max(0,min(100, 88 + min(8, concrete_bonus//10) - len(cliché_hits)*8 - max(0, int(100-variety)-35)))
    hook_score=max(0,min(100, memorability + (8 if len(hook.split())<=7 else 0) - len(cliché_hits)*6))
    emotion=max(0,min(100, 58 + min(25, len(lines)*2) + (8 if chorus else 0)))
    quotability=max(0,min(100, hook_score*0.65 + originality*0.35))
    hit_score=round(0.23*hook_score + 0.19*originality + 0.15*emotion + 0.15*singability + 0.12*quotability + 0.10*min(100,structure_score) + 0.06*variety)
    return {
        "line_count":len(lines), "word_count":total, "unique_words":unique,
        "repetition_percent":round(repeated/total*100,1) if total else 0,
        "average_words_per_line":round(avg,1), "syllable_range":spread,
        "hook":hook[:180], "sections":structure, "cliche_hits":cliché_hits,
        "hit_score":hit_score,
        "scores":{
            "hook_memorability":round(memorability), "originality":round(originality),
            "emotion":round(emotion), "word_variety":round(variety), "singability":round(singability),
            "quotability":round(quotability), "structure":min(100,structure_score)
        },
        "quality_gate":{
            "status":"PASS" if hit_score >= 82 and not cliché_hits else "REWORK",
            "priority":"hook" if hook_score < 82 else ("originality" if originality < 82 else "prosody" if singability < 82 else "ready"),
            "cliche_count":len(cliché_hits)
        },
        "notes":[
            "Hit Score — эвристический editorial score, а не прогноз чарта.",
            "Ударения и мелодия требуют проверки на реальном topline.",
            "Если Quality Gate = REWORK, сначала перепиши слабый hook/клише, затем повтори оценку."
        ]
    }
