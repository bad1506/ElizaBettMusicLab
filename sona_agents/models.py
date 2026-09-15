from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SkillSpec:
    """Нормализованное описание skill независимо от его исходного формата."""

    name: str
    description: str
    source: str
    path: str
    version: str | None = None
    license: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    instructions: str = ""


@dataclass(frozen=True)
class AgentRequest:
    """Запрос к SØNA Agent Router."""

    message: str
    skill: str | None = None
    history: list[dict[str, str]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentResponse:
    """Единый результат любого агентного вызова."""

    answer: str
    agent: str
    skill: str
    prompt_refs: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
