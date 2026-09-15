from __future__ import annotations

import logging
from typing import Any

from .base import ToolError, ToolSpec
from .music import analyze_mix, build_mix_advice

LOGGER = logging.getLogger("sona.agents.tools")


_TOOLS = {
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
            "additionalProperties": False,
        },
        handler=build_mix_advice,
    ),
}


def list_tools() -> list[dict[str, Any]]:
    """Публичный каталог инструментов без внутренних обработчиков."""
    return [spec.public() for spec in _TOOLS.values()]


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
