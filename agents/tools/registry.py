from __future__ import annotations

import logging
from typing import Any

from .base import ToolError, ToolSpec
from .music import (
    analyze_mix,
    build_mix_advice,
    get_current_intelligence,
    get_current_melody_map,
    get_current_music_analysis,
    get_current_timeline,
    get_current_vocal_context,
)

LOGGER = logging.getLogger("sona.agents.tools")


_EMPTY_INPUT = {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": False,
}


def _tool(name: str, description: str, handler) -> ToolSpec:
    return ToolSpec(name=name, description=description, input_schema=_EMPTY_INPUT, handler=handler)


_TOOLS = {
    "music.get_current_analysis": _tool(
        "music.get_current_analysis",
        "Получает актуальный read-only /analysis последнего аудиофайла текущего пользователя, включая timeline, intelligence, decisions и master brain.",
        get_current_music_analysis,
    ),
    "music.get_current_timeline": _tool(
        "music.get_current_timeline",
        "Получает waveform и сегментный loudness timeline текущего аудиотрека пользователя; только чтение.",
        get_current_timeline,
    ),
    "music.get_current_intelligence": _tool(
        "music.get_current_intelligence",
        "Получает сегментный spectral, stereo, transient и vocal intelligence текущего аудиотрека; только чтение.",
        get_current_intelligence,
    ),
    "music.get_current_vocal_context": _tool(
        "music.get_current_vocal_context",
        "Получает tempo, key, структурные секции и vocal activity текущего трека; только чтение.",
        get_current_vocal_context,
    ),
    "music.get_current_melody_map": _tool(
        "music.get_current_melody_map",
        "Получает оценочную melody map текущего трека для анализа мелодии и вокальной линии; только чтение.",
        get_current_melody_map,
    ),
    "music.analyze_mix": ToolSpec(
        name="music.analyze_mix",
        description="Структурирует результаты анализа микса, проблемы и приоритеты обработки.",
        input_schema={
            "type": "object",
            "properties": {
                "analysis": {"type": "object"},
                "decisions": {"type": "array", "items": {"type": "object"}},
                "master_report": {"type": "object"},
            },
            "required": ["analysis", "decisions", "master_report"],
            "additionalProperties": False,
        },
        handler=analyze_mix,
    ),
    "music.build_advice": ToolSpec(
        name="music.build_advice",
        description="Формирует локальные рекомендации по миксу без вызова LLM.",
        input_schema={
            "type": "object",
            "properties": {
                "analysis": {"type": "object"},
                "decisions": {"type": "array", "items": {"type": "object"}},
                "master_report": {"type": "object"},
            },
            "required": ["analysis", "decisions", "master_report"],
            "additionalProperties": False,
        },
        handler=build_mix_advice,
    ),
}


def list_tools() -> list[dict[str, Any]]:
    """Публичный каталог инструментов без внутренних обработчиков."""
    return [spec.public() for spec in _TOOLS.values()]


def get_tool_specs(names: list[str]) -> list[dict[str, Any]]:
    """Преобразует allowlist runtime-инструментов в Responses API schemas."""
    result = []
    for name in names:
        spec = _TOOLS.get(name)
        if spec is None:
            raise ToolError(f"Unknown configured tool: {name}")
        public = spec.public()
        result.append(
            {
                "type": "function",
                "name": public["name"],
                "description": public["description"],
                "parameters": public["input"],
                "strict": True,
            }
        )
    return result


def execute_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Выполняет только явно зарегистрированный инструмент."""
    spec = _TOOLS.get(name)
    if spec is None:
        raise ToolError(f"Unknown tool: {name}")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise ToolError("Tool arguments must be an object")
    try:
        return spec.handler(**arguments)
    except ToolError:
        raise
    except Exception as exc:
        LOGGER.exception("Tool execution failed: %s", name)
        raise ToolError("Tool temporarily unavailable") from exc
