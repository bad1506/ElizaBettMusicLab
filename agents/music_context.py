from __future__ import annotations

from pathlib import Path
from typing import Any

import security

ROOT = Path(__file__).resolve().parents[1]
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}

# One bounded snapshot per user. The audio identity changes when a new/replaced file
# becomes the latest input, so stale data is discarded automatically.
_MUSIC_SNAPSHOT_CACHE: dict[str, tuple[tuple[str, int, int], dict[str, Any]]] = {}


def _latest_audio() -> Path | None:
    folder = security.user_storage(ROOT)["input"]
    candidates = [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in AUDIO_EXTS]
    return max(candidates, key=lambda path: path.stat().st_mtime_ns) if candidates else None


def _audio_or_none() -> Path:
    path = _latest_audio()
    if path is None:
        raise FileNotFoundError("No audio uploaded for the current user")
    return path


def _audio_identity(path: Path) -> tuple[str, int, int]:
    stat = path.stat()
    return (str(path.resolve()), stat.st_mtime_ns, stat.st_size)


def clear_music_snapshot_cache(user_id: str | None = None) -> None:
    """Очищает snapshot cache для пользователя или весь cache."""
    if user_id is None:
        _MUSIC_SNAPSHOT_CACHE.clear()
    else:
        _MUSIC_SNAPSHOT_CACHE.pop(str(user_id), None)


def _build_music_snapshot(path: Path) -> dict[str, Any]:
    """Однократно собирает все тяжёлые audio-derived данные для текущего файла."""
    import audio_intelligence
    import audio_timeline
    import audio_to_song
    import master_engine
    import melody_alignment

    analysis = master_engine.analyze_file(path)
    if not isinstance(analysis, dict):
        raise ValueError("Master analysis returned an invalid result")

    audio = audio_to_song.analyze(path)
    if not isinstance(audio, dict):
        audio = {}

    intelligence = audio_intelligence.analyze_audio(path, segment_sec=5.0)
    if not isinstance(intelligence, dict):
        intelligence = {}

    timeline = audio_timeline.build_timeline(path)
    if not isinstance(timeline, dict):
        timeline = {}

    tempo = audio.get("tempo") if isinstance(audio.get("tempo"), dict) else {}
    bpm = tempo.get("bpm")
    melody_map = melody_alignment.analyze(path, bpm=bpm)
    if not isinstance(melody_map, dict):
        melody_map = {}

    return {
        "status": "ok",
        "file": path.name,
        "analysis": analysis,
        "audio_context": audio,
        "intelligence": intelligence,
        "timeline": timeline,
        "melody_map": melody_map,
    }


def _get_music_snapshot(path: Path) -> dict[str, Any]:
    user_id = security.current_user_id()
    identity = _audio_identity(path)
    cached = _MUSIC_SNAPSHOT_CACHE.get(user_id)
    if cached is not None and cached[0] == identity:
        return cached[1]

    snapshot = _build_music_snapshot(path)
    _MUSIC_SNAPSHOT_CACHE[user_id] = (identity, snapshot)
    return snapshot


def current_analysis() -> dict[str, Any] | None:
    """Возвращает актуальный read-only /analysis последнего аудиофайла текущего пользователя."""
    path = _latest_audio()
    if path is None:
        return None
    try:
        snapshot = _get_music_snapshot(path)
    except Exception:
        return None
    return {"status": "ok", "file": path.name, "analysis": snapshot["analysis"]}


def current_timeline() -> dict[str, Any]:
    """Возвращает waveform/loudness timeline текущего пользовательского трека."""
    path = _audio_or_none()
    snapshot = _get_music_snapshot(path)
    return {"status": "ok", "file": path.name, **snapshot["timeline"]}


def current_intelligence() -> dict[str, Any]:
    """Возвращает сегментный spectral/stereo/transient/vocal intelligence текущего трека."""
    path = _audio_or_none()
    snapshot = _get_music_snapshot(path)
    return {"status": "ok", "file": path.name, **snapshot["intelligence"]}


def current_vocal_context() -> dict[str, Any]:
    """Возвращает музыкальный контекст вокала и структуры текущего трека."""
    path = _audio_or_none()
    snapshot = _get_music_snapshot(path)
    return {"status": "ok", "file": path.name, "audio_context": snapshot["audio_context"]}


def current_melody_map() -> dict[str, Any]:
    """Возвращает оценочную melody map текущего трека."""
    path = _audio_or_none()
    snapshot = _get_music_snapshot(path)
    return {"status": "ok", "file": path.name, "melody_map": snapshot["melody_map"]}


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
    """Собирает единый read-only отчёт для AI Music Engineer из одного cached snapshot."""
    path = _latest_audio()
    if path is None:
        return {"status": "no_audio", "message": "У текущего пользователя нет доступного аудиофайла для анализа."}

    try:
        snapshot = _get_music_snapshot(path)
    except Exception:
        return {"status": "no_audio", "message": "Не удалось построить анализ текущего аудиофайла."}

    analysis = snapshot.get("analysis") if isinstance(snapshot.get("analysis"), dict) else {}
    audio = snapshot.get("audio_context") if isinstance(snapshot.get("audio_context"), dict) else {}
    intelligence = snapshot.get("intelligence") if isinstance(snapshot.get("intelligence"), dict) else {}
    timeline = snapshot.get("timeline") if isinstance(snapshot.get("timeline"), dict) else {}
    melody = snapshot.get("melody_map") if isinstance(snapshot.get("melody_map"), dict) else {}

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
        "melody": melody,
        "mix": {
            "loudness": timeline.get("loudness") if isinstance(timeline.get("loudness"), dict) else {},
            "intelligence": {"spectral": intelligence.get("spectral"), "stereo": intelligence.get("stereo"), "transients": intelligence.get("transients"), "vocal_events": intelligence.get("vocal_events")},
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
