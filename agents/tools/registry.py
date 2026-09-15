from __future__ import annotations

import logging
from typing import Any

from . import music as music_tools
from .base import ToolError, ToolSpec
from .music import (
    analyze_mix,
    build_mix_advice,
    diagnose_vocal_section,
    get_current_intelligence,
    get_current_melody_map,
    get_current_music_analysis,
    get_current_timeline,
    get_current_vocal_context,
)

LOGGER = logging.getLogger("sona.agents.tools")

_EMPTY_INPUT = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
_MIX_INPUT = {
    "type": "object",
    "properties": {
        "analysis": {"type": "object"},
        "decisions": {"type": "array", "items": {"type": "object"}},
        "master_report": {"type": "object"},
    },
    "required": ["analysis", "decisions", "master_report"],
    "additionalProperties": False,
}


def current_music_intelligence() -> dict[str, Any]:
    """Прокси для unified report; делегирует модулю music_context."""
    from ..music_context import current_music_intelligence as build_report
    return build_report()


# Compatibility alias: existing callers/tests may patch agents.tools.music.current_music_intelligence.
if not hasattr(music_tools, "current_music_intelligence"):
    setattr(music_tools, "current_music_intelligence", current_music_intelligence)


def _tool(name: str, description: str, handler) -> ToolSpec:
    return ToolSpec(name=name, description=description, input_schema=_EMPTY_INPUT, handler=handler)


_TOOLS = {
    "music.get_current_analysis": _tool("music.get_current_analysis", "Получает актуальный read-only /analysis последнего аудиофайла текущего пользователя.", get_current_music_analysis),
    "music.get_current_timeline": _tool("music.get_current_timeline", "Получает waveform и сегментный loudness timeline текущего трека; только чтение.", get_current_timeline),
    "music.get_current_intelligence": _tool("music.get_current_intelligence", "Получает spectral, stereo, transient и vocal intelligence текущего трека; только чтение.", get_current_intelligence),
    "music.get_current_vocal_context": _tool("music.get_current_vocal_context", "Получает BPM, key, структурные секции и vocal activity текущего трека; только чтение.", get_current_vocal_context),
    "music.get_current_melody_map": _tool("music.get_current_melody_map", "Получает оценочную melody map текущего трека; только чтение.", get_current_melody_map),
    "music.get_current_intelligence_report": _tool("music.get_current_intelligence_report", "Собирает единый read-only Music Intelligence отчёт: BPM, тональность, структуру, вокал, melody, loudness, spectral/stereo intelligence, engine decisions и приоритеты.", lambda: current_music_intelligence()),
    "music.diagnose_vocal_in_section": ToolSpec(name="music.diagnose_vocal_in_section", description="Диагностирует, почему вокал может теряться в секции. Если время не задано, автоматически выбирает вероятный chorus/drop или секцию по section_name.", input_schema={"type": "object", "properties": {"section_start_sec": {"type": "number", "minimum": 0}, "section_end_sec": {"type": "number", "exclusiveMinimum": 0}, "section_name": {"type": "string", "minLength": 1, "maxLength": 40}}, "required": [], "additionalProperties": False}, handler=diagnose_vocal_section),
    "music.analyze_mix": ToolSpec(name="music.analyze_mix", description="Структурирует результаты анализа микса, проблемы и приоритеты обработки.", input_schema=_MIX_INPUT, handler=analyze_mix),
    "music.build_advice": ToolSpec(name="music.build_advice", description="Формирует локальные рекомендации по миксу без вызова LLM.", input_schema=_MIX_INPUT, handler=build_mix_advice),
}


def list_tools() -> list[dict[str, Any]]:
    return [spec.public() for spec in _TOOLS.values()]


def get_tool_specs(names: list[str]) -> list[dict[str, Any]]:
    result = []
    for name in names:
        spec = _TOOLS.get(name)
        if spec is None:
            raise ToolError(f"Unknown configured tool: {name}")
        public = spec.public()
        result.append({"type": "function", "name": public["name"], "description": public["description"], "parameters": public["input"], "strict": True})
    return result


def execute_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = _TOOLS.get(name)
    if spec is None:
        raise ToolError(f"Unknown tool: {name}")
    arguments = {} if arguments is None else arguments
    if not isinstance(arguments, dict):
        raise ToolError("Tool arguments must be an object")
    try:
        return spec.handler(**arguments)
    except ToolError:
        raise
    except Exception as exc:
        LOGGER.exception("Tool execution failed: %s", name)
        raise ToolError("Tool temporarily unavailable") from exc
