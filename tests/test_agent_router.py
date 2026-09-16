from __future__ import annotations

import json

import pytest

from agents import router


class FakeProvider:
    def generate(self, *, system, messages):
        return "Тестовый ответ SØNA"

    def generate_with_tools(self, *, system, messages, tools, execute_tool, max_rounds):
        return "Тестовый ответ SØNA", []


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
    monkeypatch.setitem(router._PROVIDERS, "openai", FakeProvider())

    result = router.invoke(
        "songwriter",
        "Придумай припев",
        history=[{"role": "user", "text": "Предыдущая тема"}],
        context={"project": "TEST"},
        user_id="test-user",
    )

    assert result["ok"] is True
    assert result["answer"] == "Тестовый ответ SØNA"
    assert result["provider"] == "openai"
    assert result["skill"] == "songwriter"
