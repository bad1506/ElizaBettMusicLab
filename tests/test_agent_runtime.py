from __future__ import annotations

import json
from pathlib import Path

import sona_agents.router as router_module
from sona_agents.models import AgentRequest
from sona_agents.registry import SkillRegistry


ROOT = Path(__file__).resolve().parents[1]


def test_registry_loads_native_sona_skills():
    registry = SkillRegistry(ROOT / ".sona" / "skills", ROOT / "sona_agents" / "config.json")
    assert registry.get("assistant") is not None
    assert registry.get("songwriter") is not None
    assert registry.get("mastering") is not None


def test_registry_parses_agentskills_frontmatter(tmp_path):
    skills = tmp_path / "skills" / "external" / "demo"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: Demo skill.\nversion: 1.0.0\nlicense: MIT\nmetadata:\n  hermes:\n    tags: [demo]\n---\n# Demo\n\nDo the demo.\n",
        encoding="utf-8",
    )
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"default_agent": "a", "agents": {"a": {"default_skill": "demo-skill"}}}), encoding="utf-8")

    registry = SkillRegistry(tmp_path / "skills", config)
    skill = registry.get("demo-skill")
    assert skill is not None
    assert skill.version == "1.0.0"
    assert "Do the demo" in skill.instructions


def test_router_selects_skill_and_returns_answer(monkeypatch):
    monkeypatch.setattr(router_module, "search_prompts", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(router_module.ai_assistant, "_openai_model", lambda: "test-model")
    monkeypatch.setattr(router_module.ai_assistant, "_openai", lambda payload, timeout: "готовый ответ")

    router = router_module.AgentRouter()
    result = router.run(AgentRequest(message="Давай напишем припев для новой песни"))

    assert result.answer == "готовый ответ"
    assert result.skill == "songwriter"
    assert result.agent == "sona-assistant"
