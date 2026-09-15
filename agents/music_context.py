from __future__ import annotations

from pathlib import Path
from typing import Any

import audio_intelligence
import audio_timeline
import audio_to_song
import master_engine
import melody_alignment
import security

ROOT = Path(__file__).resolve().parents[1]
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}


def _latest_audio() -> Path | None:
    folder = security.user_storage(ROOT)["input"]
    candidates = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in AUDIO_EXTS
    ]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def _audio_or_none() -> Path:
    path = _latest_audio()
    if path is None:
        raise FileNotFoundError("No audio uploaded for the current user")
    return path


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
    return {"status": "ok", "file": path.name, "analysis": analysis}


def current_timeline() -> dict[str, Any]:
    """Возвращает waveform/loudness timeline текущего пользовательского трека."""
    path = _audio_or_none()
    return {"status": "ok", "file": path.name, **audio_timeline.build_timeline(path)}


def current_intelligence() -> dict[str, Any]:
    """Возвращает сегментный spectral/stereo/transient/vocal intelligence текущего трека."""
    path = _audio_or_none()
    return {
        "status": "ok",
        "file": path.name,
        **audio_intelligence.analyze_audio(path, segment_sec=5.0),
    }


def current_vocal_context() -> dict[str, Any]:
    """Возвращает музыкальный контекст вокала и структуры текущего трека."""
    path = _audio_or_none()
    return {"status": "ok", "file": path.name, "audio_context": audio_to_song.analyze(path)}


def current_melody_map() -> dict[str, Any]:
    """Возвращает оценочную melody map текущего трека."""
    path = _audio_or_none()
    audio = audio_to_song.analyze(path)
    bpm = (audio.get("tempo") or {}).get("bpm")
    return {
        "status": "ok",
        "file": path.name,
        "melody_map": melody_alignment.analyze(path, bpm=bpm),
    }
