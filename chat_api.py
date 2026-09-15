from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from sona_agents import AgentRequest, AgentRouter


router = AgentRouter()


class ChatMessage(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    text: str = Field(min_length=1, max_length=12000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=30)
    context: dict[str, Any] = Field(default_factory=dict)


class AgentRunRequest(ChatRequest):
    """Запрос для явного вызова конкретного skill."""

    skill: str | None = Field(default=None, max_length=80)
    agent: str | None = Field(default=None, max_length=80)


def _run(request: ChatRequest, *, skill: str | None = None, agent: str | None = None):
    context = dict(request.context)
    if skill:
        context["skill"] = skill
    if agent:
        context["agent"] = agent

    try:
        result = router.run(
            AgentRequest(
                message=request.message,
                skill=skill,
                history=[item.model_dump() for item in request.history[-20:]],
                context=context,
            )
        )
    except Exception as exc:
        raise HTTPException(502, "SØNA Agent Runtime временно недоступен. Проверьте AI API на backend.") from exc

    return {
        "ok": True,
        "answer": result.answer,
        "agent": result.agent,
        "skill": result.skill,
        "prompt_refs": result.prompt_refs,
        "metadata": result.metadata,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def register(app):
    @app.post("/sona-chat")
    def chat(request: ChatRequest):
        # Основной пользовательский чат. Роутинг skill происходит автоматически.
        return _run(request)

    @app.post("/agents/run")
    def run_agent(request: AgentRunRequest):
        # Универсальный backend-интерфейс для UI, автоматизаций и будущих клиентов.
        return _run(request, skill=request.skill, agent=request.agent)

    @app.get("/agents/skills")
    def list_agent_skills():
        return {"ok": True, "skills": router.list_skills()}
