from __future__ import annotations

from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent / ".sona" / "skills"
DEFAULT_SKILL = "assistant"

@lru_cache(maxsize=32)
def load_skill(name: str) -> str:
    safe = "".join(ch for ch in (name or DEFAULT_SKILL).lower() if ch.isalnum() or ch in "-_") or DEFAULT_SKILL
    path = ROOT / f"{safe}.md"
    if not path.is_file():
        path = ROOT / f"{DEFAULT_SKILL}.md"
    try:
        return path.read_text(encoding="utf-8")[:18000]
    except OSError:
        return ""

def skill_context(name: str) -> str:
    text = load_skill(name)
    return f"\n\nSØNA SKILL: {name or DEFAULT_SKILL}\n{text}" if text else ""
