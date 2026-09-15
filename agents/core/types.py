from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentRequest:
    """Нормализованный запрос к agent runtime."""

    agent: str
    message: str
    history: list[dict[str, str]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    user_id: str = "anonymous"


@dataclass(slots=True)
class AgentResponse:
    """Нормализованный ответ provider-а."""

    answer: str
    agent: str
    provider: str
    sources: list[dict[str, Any]] = field(default_factory=list)
