from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from agents.router import AgentError, invoke as invoke_agent, list_agents
import security


class ChatMessage(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    text: str = Field(min_length=1, max_length=12000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=30)
    context: dict[str, Any] = Field(default_factory=dict)


class AgentRunRequest(ChatRequest):
    """Запрос для явного вызова зарегистрированного SØNA agent."""

    skill: str | None = Field(default=None, max_length=80)
    agent: str | None = Field(default=None, max_length=80)


def _resolve_agent(*, agent: str | None, skill: str | None) -> str:
    agents = list_agents()
    if agent:
        if agent not in agents:
            raise HTTPException(400, f"Unknown agent: {agent}")
        return agent

    requested_skill = (skill or "").strip()
    if requested_skill:
        matches = [
            name for name, spec in agents.items()
            if isinstance(spec, dict) and str(spec.get("skill") or "") == requested_skill
        ]
        if matches:
            return matches[0]
        raise HTTPException(400, f"Unknown skill: {requested_skill}")

    return "assistant"


def _run(request: ChatRequest, *, skill: str | None = None, agent: str | None = None):
    context = dict(request.context or {})
    requested_skill = (skill or str(context.get("skill") or "").strip() or None)
    selected_agent = _resolve_agent(
        agent=agent or str(context.get("agent") or "").strip() or None,
        skill=requested_skill,
    )

    # Never forward credentials supplied by a client as model context.
    context.pop("authorization", None)
    context.pop("token", None)
    context.pop("skill", None)
    context.pop("agent", None)

    try:
        result = invoke_agent(
            selected_agent,
            request.message,
            history=[item.model_dump() for item in request.history[-20:]],
            context=context,
            user_id=security.current_user_id(),
        )
    except AgentError as exc:
        raise HTTPException(502, "SØNA Agent Runtime временно недоступен. Проверьте AI API на backend.") from exc

    return {
        "ok": True,
        "answer": result["answer"],
        "agent": result["agent"],
        "skill": result["skill"],
        "sources": result.get("sources", []),
        "tool_calls": result.get("tool_calls", []),
        "metadata": {
            "provider": result.get("provider"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def register(app):
    @app.post("/sona-chat")
    def chat(request: ChatRequest):
        # Основной пользовательский чат использует тот же agents/ runtime,
        # что и /agents/invoke: единый registry, skills, tools и security boundary.
        return _run(request)

    @app.post("/agents/run")
    def run_agent(request: AgentRunRequest):
        # Универсальный backend-интерфейс для UI, автоматизаций и будущих клиентов.
        return _run(request, skill=request.skill, agent=request.agent)

    @app.get("/agents/skills")
    def list_agent_skills():
        return {
            "ok": True,
            "skills": [
                {
                    "name": spec.get("skill", name),
                    "agent": name,
                    "description": spec.get("description", ""),
                    "source": spec.get("source", "local"),
                }
                for name, spec in list_agents().items()
            ],
        }
