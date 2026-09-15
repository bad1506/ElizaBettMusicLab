from __future__ import annotations

from statistics import median
from typing import Any

import ai_assistant

from ..music_context import (
    current_analysis,
    current_intelligence,
    current_melody_map,
    current_timeline,
    current_vocal_context,
)
from .base import ToolError


def _dict(value: Any, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ToolError(f"{field} must be an object")
    return value


def get_current_music_analysis() -> dict[str, Any]:
    """Возвращает актуальный read-only /analysis последнего аудио текущего пользователя."""
    result = current_analysis()
    if result is None:
        return {"status": "no_audio", "message": "У текущего пользователя нет доступного аудиофайла для анализа."}
    return result


def _read_only_call(handler, label: str) -> dict[str, Any]:
    try:
        return handler()
    except FileNotFoundError as exc:
        raise ToolError("No audio is available for the current user") from exc
    except Exception as exc:
        raise ToolError(f"{label} temporarily unavailable") from exc


def get_current_timeline() -> dict[str, Any]:
    return _read_only_call(current_timeline, "Timeline")


def get_current_intelligence() -> dict[str, Any]:
    return _read_only_call(current_intelligence, "Audio intelligence")


def get_current_vocal_context() -> dict[str, Any]:
    return _read_only_call(current_vocal_context, "Vocal context")


def get_current_melody_map() -> dict[str, Any]:
    return _read_only_call(current_melody_map, "Melody map")


def _overlap(item: dict[str, Any], start: float, end: float) -> bool:
    try:
        return float(item.get("end", 0.0)) > start and float(item.get("start", 0.0)) < end
    except (TypeError, ValueError):
        return False


def _median_metric(items: list[dict[str, Any]], key: str) -> float | None:
    values = []
    for item in items:
        try:
            values.append(float(item[key]))
        except (KeyError, TypeError, ValueError):
            continue
    return float(median(values)) if values else None


def _select_section(section_name: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Выбирает секцию по роли/номеру или автоматически — наиболее вероятный chorus/drop."""
    context = current_vocal_context()
    audio = _dict(context.get("audio_context"), "audio_context")
    sections = audio.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ToolError("No structural sections were detected")
    valid = [item for item in sections if isinstance(item, dict) and _valid_section(item)]
    if not valid:
        raise ToolError("Detected sections have invalid boundaries")
    query = (section_name or "").strip().lower()
    if query:
        try:
            index = int(query)
            for item in valid:
                if int(item.get("index")) == index:
                    return item, valid
        except (ValueError, TypeError):
            pass
        aliases = {
            "intro": ("intro", "opening"),
            "verse": ("verse", "куплет"),
            "куплет": ("verse", "куплет"),
            "prechorus": ("pre-chorus", "pre chorus", "припев"),
            "pre-chorus": ("pre-chorus", "pre chorus"),
            "припев": ("chorus", "припев", "drop"),
            "chorus": ("chorus", "припев", "drop"),
            "drop": ("drop", "chorus"),
            "bridge": ("bridge", "бридж"),
            "бридж": ("bridge", "бридж"),
            "outro": ("outro", "final", "финал"),
            "финал": ("outro", "final", "финал"),
        }
        wanted = aliases.get(query, (query,))
        for item in valid:
            haystack = " ".join(str(item.get(k, "")) for k in ("role_hint", "energy_label", "label", "role")).lower()
            if any(alias in haystack for alias in wanted):
                return item, valid
        raise ToolError(f"Section '{section_name}' was not found")

    chorus_candidates = [item for item in valid if "chorus" in str(item.get("role_hint", "")).lower() or "drop" in str(item.get("role_hint", "")).lower()]
    if chorus_candidates:
        return max(chorus_candidates, key=lambda item: float(item.get("energy_db_relative", 0.0))), valid
    return max(valid, key=lambda item: float(item.get("energy_db_relative", 0.0))), valid


def _valid_section(item: dict[str, Any]) -> bool:
    try:
        return float(item["end"]) > float(item["start"]) and float(item["start"]) >= 0
    except (KeyError, TypeError, ValueError):
        return False


def diagnose_vocal_section(*, section_start_sec: float | None = None, section_end_sec: float | None = None, section_name: str | None = None) -> dict[str, Any]:
    """Диагностирует, почему вокал может теряться; границы секции можно определить автоматически."""
    selected: dict[str, Any] | None = None
    detected_sections: list[dict[str, Any]] = []
    if section_start_sec is None or section_end_sec is None:
        selected, detected_sections = _select_section(section_name)
        start = float(selected["start"])
        end = float(selected["end"])
    else:
        start = float(section_start_sec)
        end = float(section_end_sec)
    if start < 0 or end <= start:
        raise ToolError("section_end_sec must be greater than section_start_sec")
    if end - start > 120:
        raise ToolError("Section window is too large; maximum is 120 seconds")

    snapshot = current_analysis()
    if snapshot is None:
        return {"status": "no_audio", "message": "У текущего пользователя нет доступного аудиофайла для анализа."}
    analysis = _dict(snapshot.get("analysis"), "analysis")
    intelligence = _dict(analysis.get("intelligence"), "intelligence")
    timeline = _dict(analysis.get("timeline"), "timeline")
    spectral = _dict(intelligence.get("spectral"), "spectral").get("segments", [])
    stereo = _dict(intelligence.get("stereo"), "stereo").get("segments", [])
    vocal = _dict(intelligence.get("vocal_events"), "vocal_events").get("events", [])
    transients = _dict(intelligence.get("transients"), "transients").get("events", [])
    loudness = _dict(timeline.get("loudness"), "loudness").get("segments", [])
    if not all(isinstance(group, list) for group in (spectral, stereo, vocal, transients, loudness)):
        raise ToolError("Current analysis has an invalid segment structure")

    section_spectral = [x for x in spectral if _overlap(x, start, end)]
    section_stereo = [x for x in stereo if _overlap(x, start, end)]
    section_vocal = [x for x in vocal if _overlap(x, start, end)]
    section_transients = [x for x in transients if _overlap(x, start, end)]
    section_loudness = [x for x in loudness if _overlap(x, start, end)]
    outside_spectral = [x for x in spectral if not _overlap(x, start, end)]
    outside_stereo = [x for x in stereo if not _overlap(x, start, end)]
    if not section_spectral:
        return {"status": "insufficient_data", "section": {"start_sec": start, "end_sec": end}, "message": "Для указанного участка нет spectral segment data."}

    def delta(key: str) -> float | None:
        a = _median_metric(section_spectral, key)
        b = _median_metric(outside_spectral, key)
        return round(a - b, 2) if a is not None and b is not None else None

    band_deltas: dict[str, float] = {}
    bands = (section_spectral[0].get("bands") or {}).keys()
    for band in bands:
        a = _median_metric([x.get("bands", {}) for x in section_spectral], band)
        b = _median_metric([x.get("bands", {}) for x in outside_spectral], band)
        if a is not None and b is not None:
            band_deltas[band] = round(a - b, 2)

    issues: list[dict[str, Any]] = []
    presence_delta = band_deltas.get("presence")
    low_mid_delta = band_deltas.get("low_mid")
    mid_delta = band_deltas.get("mid")
    bass_delta = band_deltas.get("bass")
    if low_mid_delta is not None and low_mid_delta >= 3.0:
        issues.append({"cause": "low_mid_masking", "severity": "high", "evidence": f"150–500 Hz is {low_mid_delta:+.1f} percentage points vs outside section", "recommendation": "Проверить конкуренцию инструментов в 150–500 Hz и сделать динамическое место для основного вокала."})
    if presence_delta is not None and presence_delta <= -2.0:
        issues.append({"cause": "presence_loss", "severity": "high", "evidence": f"2–6 kHz is {presence_delta:+.1f} percentage points vs outside section", "recommendation": "Проверить зону разборчивости вокала; сначала сравнить вокал с инструменталом, затем применять умеренный dynamic EQ/automation."})
    if presence_delta is not None and presence_delta >= 5.0:
        issues.append({"cause": "presence_competition", "severity": "medium", "evidence": f"2–6 kHz rises {presence_delta:+.1f} percentage points vs outside section", "recommendation": "Проверить конкурирующие синты, гитары, снейр и сатурацию в 2–6 kHz; приоритет — ducking конкурирующих источников."})
    if mid_delta is not None and mid_delta >= 5.0:
        issues.append({"cause": "mid_density", "severity": "medium", "evidence": f"500 Hz–2 kHz is {mid_delta:+.1f} percentage points vs outside section", "recommendation": "Проверить плотность midrange: накопление инструментов здесь часто уменьшает читаемость вокала."})
    if bass_delta is not None and bass_delta >= 6.0:
        issues.append({"cause": "low_end_energy", "severity": "low", "evidence": f"60–150 Hz rises {bass_delta:+.1f} percentage points", "recommendation": "Проверить, не вызывает ли усиление низов дополнительное срабатывание bus/master compression и pumping."})
    section_corr = _median_metric(section_stereo, "correlation")
    outside_corr = _median_metric(outside_stereo, "correlation")
    if section_corr is not None and outside_corr is not None and section_corr < outside_corr - 0.25:
        issues.append({"cause": "stereo_masking_or_phase", "severity": "medium", "evidence": f"Stereo correlation drops to {section_corr:.2f} vs {outside_corr:.2f} outside", "recommendation": "Проверить widened effects и side-heavy layers вокруг вокала; сравнить в mono перед дальнейшим EQ."})
    vocal_voiced = _median_metric(section_vocal, "voiced_percent")
    section_lufs = _median_metric(section_loudness, "lufs")
    outside_lufs = _median_metric([x for x in loudness if not _overlap(x, start, end)], "lufs")
    transient_count = sum(int(x.get("count", 0) or 0) for x in section_transients)
    if section_lufs is not None and outside_lufs is not None and section_lufs - outside_lufs > 2.5:
        issues.append({"cause": "density_and_bus_compression", "severity": "medium", "evidence": f"Section loudness is {section_lufs - outside_lufs:+.1f} LU vs outside", "recommendation": "Проверить gain staging и bus/master compression: более плотная секция может уменьшать относительную разборчивость вокала."})
    if not issues:
        issues.append({"cause": "no_single_dominant_cause", "severity": "low", "evidence": "Сегментные метрики не показывают одного явного виновника.", "recommendation": "Сравнить vocal stem с instrumental stem и проверить clip gain/automation перед широкими EQ-изменениями."})
    priority = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda item: priority[item["severity"]])
    result = {
        "status": "ok",
        "file": snapshot.get("file"),
        "section": {"start_sec": round(start, 3), "end_sec": round(end, 3), "duration_sec": round(end - start, 3)},
        "vocal": {"median_voiced_percent": round(vocal_voiced, 1) if vocal_voiced is not None else None},
        "metrics": {"band_delta_percentage_points_vs_outside": band_deltas, "spectral_centroid_delta_hz": delta("centroid_hz"), "rolloff_delta_hz": delta("rolloff_hz"), "section_lufs": round(section_lufs, 2) if section_lufs is not None else None, "outside_lufs": round(outside_lufs, 2) if outside_lufs is not None else None, "stereo_correlation": round(section_corr, 3) if section_corr is not None else None, "transient_count": transient_count},
        "diagnosis": issues,
        "recommended_order": [item["recommendation"] for item in issues[:3]],
        "limitations": ["Диагностика работает по full-mix сегментам; без isolated vocal/instrumental stems она не доказывает причинность.", "Band percentages описывают распределение энергии внутри анализируемого full mix, а не абсолютную громкость вокала.", "Рекомендации read-only: инструмент не меняет аудио и не экспортирует результат."],
    }
    if selected is not None:
        result["section_selection"] = {"mode": "automatic" if not section_name else "name", "requested": section_name, "selected_index": selected.get("index"), "selected_role_hint": selected.get("role_hint"), "detected_sections": detected_sections}
    else:
        result["section_selection"] = {"mode": "explicit_time_range"}
    return result


def analyze_mix(*, analysis: dict[str, Any] | None = None, decisions: list[dict[str, Any]] | None = None, master_report: dict[str, Any] | None = None) -> dict[str, Any]:
    analysis = _dict(analysis, "analysis")
    master_report = _dict(master_report, "master_report")
    if decisions is None:
        decisions = []
    if not isinstance(decisions, list) or any(not isinstance(item, dict) for item in decisions):
        raise ToolError("decisions must be a list of objects")
    return ai_assistant.analyze_mix_intelligently(analysis=analysis, decisions=decisions, master_report=master_report)


def build_mix_advice(*, analysis: dict[str, Any] | None = None, decisions: list[dict[str, Any]] | None = None, master_report: dict[str, Any] | None = None) -> dict[str, Any]:
    analysis = _dict(analysis, "analysis")
    master_report = _dict(master_report, "master_report")
    if decisions is None:
        decisions = []
    if not isinstance(decisions, list) or any(not isinstance(item, dict) for item in decisions):
        raise ToolError("decisions must be a list of objects")
    return {"advice": ai_assistant.build_local_advice(analysis, decisions, master_report)}
