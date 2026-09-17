from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from agents.router import AgentError, invoke as invoke_agent, list_agents
import quota
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
        if agent not in agents: raise HTTPException(400, f"Unknown agent: {agent}")
        return agent
    requested_skill = (skill or "").strip()
    if requested_skill:
        matches = [name for name, spec in agents.items() if isinstance(spec, dict) and str(spec.get("skill") or "") == requested_skill]
        if matches: return matches[0]
        raise HTTPException(400, f"Unknown skill: {requested_skill}")
    return "assistant"


def _run(request: ChatRequest, *, skill: str | None = None, agent: str | None = None):
    context = dict(request.context or {})
    requested_skill = skill or str(context.get("skill") or "").strip() or None
    selected_agent = _resolve_agent(agent=agent or str(context.get("agent") or "").strip() or None, skill=requested_skill)
    context.pop("authorization", None); context.pop("token", None); context.pop("skill", None); context.pop("agent", None)
    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise HTTPException(503, "SØNA AI не настроен на backend: отсутствует OPENAI_API_KEY.")
    user_id = security.current_user_id()
    allowed, state = quota.check(user_id, "chat")
    if not allowed:
        item = state["features"]["chat"]
        raise HTTPException(402, f"Лимит AI-чата исчерпан: {item['used']}/{item['limit']}. Выберите тариф с большим лимитом.")
    try:
        result = invoke_agent(selected_agent, request.message, history=[item.model_dump() for item in request.history[-20:]], context=context, user_id=user_id)
    except AgentError as exc:
        raise HTTPException(502, "SØNA Agent Runtime временно недоступен. Проверьте AI API и backend logs.") from exc
    quota.consume(user_id, "chat")
    return {"ok": True, "answer": result["answer"], "agent": result["agent"], "skill": result["skill"], "sources": result.get("sources", []), "tool_calls": result.get("tool_calls", []), "music_report": result.get("music_report"), "music_action_report": result.get("music_action_report"), "music_action_tool": result.get("music_action_tool"), "metadata": {"provider": result.get("provider"), "generated_at": datetime.now(timezone.utc).isoformat()}, "quota": quota.usage(user_id)["features"]["chat"]}


def register(app):
    @app.post("/sona-chat")
    def chat(request: ChatRequest): return _run(request)

    @app.post("/agents/run")
    def run_agent(request: AgentRunRequest): return _run(request, skill=request.skill, agent=request.agent)

    @app.get("/agents/skills")
    def list_agent_skills():
        return {"ok": True, "skills": [{"name": spec.get("skill", name), "agent": name, "description": spec.get("description", ""), "source": spec.get("source", "local")} for name, spec in list_agents().items()]}
