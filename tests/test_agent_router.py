from __future__ import annotations

import json

import pytest

from agents import router


def test_registry_contains_core_agents():
    agents = router.list_agents()
    assert "assistant" in agents
    assert "songwriter" in agents
    assert "release-marketing" in agents
    assert "prompt-engineering" in agents


def test_unknown_agent_is_rejected():
    with pytest.raises(router.AgentError, match="Unknown agent"):
        router.invoke("does-not-exist", "hello")


def test_invoke_uses_existing_openai_provider(monkeypatch):
    monkeypatch.setattr(router, "search_prompts", lambda query, limit=5: [])
    monkeypatch.setattr(router.ai_assistant, "_openai_model", lambda: "test-model")

    captured = {}

    def fake_openai(payload, timeout):
        captured["payload"] = payload
        captured["timeout"] = timeout
        return "Тестовый ответ SØNA"

    monkeypatch.setattr(router.ai_assistant, "_openai", fake_openai)
    result = router.invoke(
        "songwriter",
        "Придумай припев",
        history=[{"role": "user", "text": "Предыдущая тема"}],
        context={"project": "TEST"},
        user_id="test-user",
    )

    assert result["ok"] is True
    assert result["answer"] == "Тестовый ответ SØNA"
    assert captured["timeout"] == 120
    serialized = json.dumps(captured["payload"], ensure_ascii=False)
    assert "Предыдущая тема" in serialized
    assert "TEST" in serialized
