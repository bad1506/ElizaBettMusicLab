from __future__ import annotations

from typing import Any

import ai_assistant

from ..music_context import current_analysis
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
        return {
            "status": "no_audio",
            "message": "У текущего пользователя нет доступного аудиофайла для анализа.",
        }
    return result


def analyze_mix(*, analysis: dict[str, Any] | None = None, decisions: list[dict[str, Any]] | None = None, master_report: dict[str, Any] | None = None) -> dict[str, Any]:
    """Формирует структурированное музыкальное заключение из данных анализатора."""
    analysis = _dict(analysis, "analysis")
    master_report = _dict(master_report, "master_report")
    if decisions is None:
        decisions = []
    if not isinstance(decisions, list) or any(not isinstance(item, dict) for item in decisions):
        raise ToolError("decisions must be a list of objects")
    return ai_assistant.analyze_mix_intelligently(
        analysis=analysis,
        decisions=decisions,
        master_report=master_report,
    )


def build_mix_advice(*, analysis: dict[str, Any] | None = None, decisions: list[dict[str, Any]] | None = None, master_report: dict[str, Any] | None = None) -> dict[str, Any]:
    """Возвращает локальные рекомендации без обращения к внешнему LLM."""
    analysis = _dict(analysis, "analysis")
    master_report = _dict(master_report, "master_report")
    if decisions is None:
        decisions = []
    if not isinstance(decisions, list) or any(not isinstance(item, dict) for item in decisions):
        raise ToolError("decisions must be a list of objects")
    return {"advice": ai_assistant.build_local_advice(analysis, decisions, master_report)}
