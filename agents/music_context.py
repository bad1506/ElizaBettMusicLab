from __future__ import annotations

from pathlib import Path
from typing import Any

import security

ROOT = Path(__file__).resolve().parents[1]
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}


def _latest_audio() -> Path | None:
    folder = security.user_storage(ROOT)["input"]
    candidates = [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in AUDIO_EXTS]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def _audio_or_none() -> Path:
    path = _latest_audio()
    if path is None:
        raise FileNotFoundError("No audio uploaded for the current user")
    return path


def current_analysis() -> dict[str, Any] | None:
    """Возвращает актуальный анализ последнего аудиофайла текущего пользователя."""
    import master_engine
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
    import audio_timeline
    path = _audio_or_none()
    return {"status": "ok", "file": path.name, **audio_timeline.build_timeline(path)}


def current_intelligence() -> dict[str, Any]:
    """Возвращает сегментный spectral/stereo/transient/vocal intelligence текущего трека."""
    import audio_intelligence
    path = _audio_or_none()
    return {"status": "ok", "file": path.name, **audio_intelligence.analyze_audio(path, segment_sec=5.0)}


def current_vocal_context() -> dict[str, Any]:
    """Возвращает музыкальный контекст вокала и структуры текущего трека."""
    import audio_to_song
    path = _audio_or_none()
    return {"status": "ok", "file": path.name, "audio_context": audio_to_song.analyze(path)}


def current_melody_map() -> dict[str, Any]:
    """Возвращает оценочную melody map текущего трека."""
    import audio_to_song
    import melody_alignment
    path = _audio_or_none()
    audio = audio_to_song.analyze(path)
    bpm = (audio.get("tempo") or {}).get("bpm")
    return {"status": "ok", "file": path.name, "melody_map": melody_alignment.analyze(path, bpm=bpm)}


def _first_number(data: dict[str, Any], *paths: tuple[str, ...]) -> float | None:
    for path in paths:
        value: Any = data
        for key in path:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            continue
    return None


def current_music_intelligence() -> dict[str, Any]:
    """Собирает единый read-only отчёт для AI Music Engineer из доступных движков."""
    snapshot = current_analysis()
    if snapshot is None:
        return {"status": "no_audio", "message": "У текущего пользователя нет доступного аудиофайла для анализа."}

    analysis = snapshot.get("analysis") if isinstance(snapshot.get("analysis"), dict) else {}
    vocal = current_vocal_context()
    audio = vocal.get("audio_context") if isinstance(vocal.get("audio_context"), dict) else {}
    intelligence = current_intelligence()
    timeline = current_timeline()
    melody = current_melody_map()

    tempo = audio.get("tempo") if isinstance(audio.get("tempo"), dict) else {}
    key = audio.get("key") if isinstance(audio.get("key"), dict) else {}
    sections = audio.get("sections") if isinstance(audio.get("sections"), list) else []
    valid_sections = []
    for item in sections:
        if not isinstance(item, dict):
            continue
        try:
            start, end = float(item["start"]), float(item["end"])
            if end > start >= 0:
                valid_sections.append({"index": item.get("index"), "start_sec": round(start, 3), "end_sec": round(end, 3), "duration_sec": round(end - start, 3), "role_hint": item.get("role_hint"), "energy_db_relative": item.get("energy_db_relative")})
        except (KeyError, TypeError, ValueError):
            continue

    intel = intelligence
    report = {
        "status": "ok",
        "file": snapshot.get("file"),
        "technical": {
            "duration_sec": _first_number(audio, ("duration",), ("duration_sec",)) or _first_number(analysis, ("duration",), ("duration_sec",)),
            "bpm": _first_number(tempo, ("bpm",), ("tempo",)),
            "key": key.get("name") or key.get("key") or audio.get("key_name") or audio.get("tonal_key"),
            "time_signature": audio.get("time_signature") or audio.get("meter"),
        },
        "structure": {"sections": valid_sections, "section_count": len(valid_sections)},
        "vocal": audio.get("vocal") or audio.get("vocals") or {},
        "melody": melody.get("melody_map") or {},
        "mix": {
            "loudness": (timeline.get("loudness") if isinstance(timeline.get("loudness"), dict) else {}),
            "intelligence": {"spectral": intel.get("spectral"), "stereo": intel.get("stereo"), "transients": intel.get("transients"), "vocal_events": intel.get("vocal_events")},
        },
        "engine": {
            "decisions": analysis.get("decisions", []),
            "processing_plan": analysis.get("processing_plan", []),
            "adaptive_analysis": analysis.get("adaptive_analysis", {}),
            "master_brain": analysis.get("master_brain", {}),
        },
        "limitations": [
            "Отчёт анализирует текущий full mix и доступные производные метрики.",
            "Без isolated stems диагностические выводы о причинности остаются вероятностными.",
            "Инструмент read-only: не изменяет аудио, проект или экспорт.",
        ],
    }

    decisions = report["engine"]["decisions"]
    if not isinstance(decisions, list):
        decisions = []
    issues = []
    for item in decisions:
        if isinstance(item, dict):
            issue = item.get("issue") or item.get("problem") or item.get("cause")
            severity = item.get("severity") or item.get("priority")
            if issue:
                issues.append({"issue": issue, "severity": severity, "evidence": item.get("evidence"), "recommendation": item.get("recommendation") or item.get("action")})
    report["issues"] = issues
    order = []
    for item in issues:
        if item.get("recommendation"):
            order.append(item["recommendation"])
    if not order:
        for item in report["engine"]["processing_plan"] if isinstance(report["engine"]["processing_plan"], list) else []:
            if isinstance(item, dict):
                action = item.get("action") or item.get("recommendation") or item.get("title")
                if action:
                    order.append(action)
    report["priority_order"] = order[:5]
    return report
