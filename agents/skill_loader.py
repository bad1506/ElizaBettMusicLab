from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCAL_SKILLS = ROOT / ".sona" / "skills"
EXTERNAL_SKILLS = ROOT / "agents" / "skills" / "external"


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Читает простой YAML frontmatter без добавления PyYAML в проект."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) != 3:
        return {}, text
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"\'')
    return meta, parts[2].lstrip()


def _safe_name(name: str) -> str:
    value = re.sub(r"[^a-z0-9_-]", "", (name or "").lower())
    return value[:100] or "assistant"


def _external_candidates(safe: str) -> list[Path]:
    """Поддерживает и плоскую, и сгруппированную структуру external skills."""
    candidates = [EXTERNAL_SKILLS / safe / "SKILL.md"]
    if EXTERNAL_SKILLS.is_dir():
        for path in EXTERNAL_SKILLS.glob(f"*/{safe}/SKILL.md"):
            candidates.append(path)
    return candidates


@lru_cache(maxsize=128)
def load(name: str) -> dict[str, Any]:
    """Загружает локальный SØNA skill или совместимый AgentSkills SKILL.md."""
    safe = _safe_name(name)
    candidates = [LOCAL_SKILLS / f"{safe}.md", *_external_candidates(safe)]

    for path in candidates:
        if not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, body = _frontmatter(raw)
        return {
            "name": meta.get("name", safe),
            "description": meta.get("description", ""),
            "version": meta.get("version", ""),
            "source": str(path.relative_to(ROOT)),
            "instructions": body[:24000],
        }

    return {
        "name": safe,
        "description": "",
        "version": "",
        "source": "missing",
        "instructions": "",
    }
