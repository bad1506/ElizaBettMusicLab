from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import master_engine
import security

ROOT = Path(__file__).resolve().parents[1]
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
MAX_CONTEXT_CHARS = max(2000, int(os.getenv("SONA_AGENT_ANALYSIS_CONTEXT_CHARS", "9000")))


def _latest_audio() -> Path | None:
    folder = security.user_storage(ROOT)["input"]
    candidates = [
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in AUDIO_EXTS
    ]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def current_analysis() -> dict[str, Any] | None:
    """Возвращает актуальный анализ последнего аудиофайла текущего пользователя."""
    path = _latest_audio()
    if path is None:
        return None
    try:
        analysis = master_engine.analyze_file(path)
    except Exception:
        return None
    if not isinstance(analysis, dict):
        return None
    return {
        "status": "ok",
        "file": path.name,
        "analysis": analysis,
    }
