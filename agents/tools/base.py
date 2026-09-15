from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class ToolError(RuntimeError):
    """Безопасная ошибка выполнения разрешённого инструмента."""


@dataclass(frozen=True)
class ToolSpec:
    """Описание инструмента, доступное runtime и UI."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., dict[str, Any]]

    def public(self) -> dict[str, Any]:
        """Возвращает описание без внутренней Python-функции."""
        return {
            "name": self.name,
            "description": self.description,
            "input": self.input_schema,
        }
