import unittest

from agents import router
from agents.skill_loader import load
from agents.tools import execute_tool, list_tools
from agents.tools.base import ToolError
from agents.tools.registry import get_tool_specs


class FakeProvider:
    def __init__(self):
        self.calls = []
        self.tool_calls = []

    def generate(self, *, system, messages):
        self.calls.append((system, messages))
        return "TEST_OK"

    def generate_with_tools(self, *, system, messages, tools, execute_tool, max_rounds):
        self.calls.append((system, messages, tools, max_rounds))
        self.tool_calls.append(tools)
        self.assert_tool = execute_tool
        result = execute_tool(
            "music.analyze_mix",
            {
                "analysis": {"crest_factor_db": 6.0},
                "decisions": [],
                "master_report": {},
            },
        )
        self.last_tool_result = result
        return "TEST_TOOL_OK", [{"name": "music.analyze_mix", "status": "ok"}]


class AgentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeProvider()
        self.original = router._PROVIDERS.get("openai")
        self.original_prompts = router._PROVIDERS.get("openai+prompts.chat")
        router._PROVIDERS["openai"] = self.fake
        router._PROVIDERS["openai+prompts.chat"] = self.fake

    def tearDown(self):
        router._PROVIDERS["openai"] = self.original
        router._PROVIDERS["openai+prompts.chat"] = self.original_prompts

    def test_registry_contains_existing_and_external_agents(self):
        agents = router.list_agents()
        self.assertIn("assistant", agents)
        self.assertIn("songwriter", agents)
        self.assertIn("songwriting-ai-music", agents)
        self.assertIn("skill-creator", agents)

    def test_every_enabled_registry_agent_has_a_real_skill(self):
        """Registry не должен содержать включённый agent с отсутствующим skill."""
        for agent_name, spec in router.list_agents().items():
            skill_name = spec.get("skill")
            self.assertIsInstance(skill_name, str, agent_name)
            skill = load(skill_name)
            self.assertNotEqual(
                skill["source"],
                "missing",
                f"Agent {agent_name!r} points to missing skill {skill_name!r}",
            )
            self.assertTrue(skill["instructions"].strip(), agent_name)

    def test_hermes_skill_is_loaded(self):
        skill = load("songwriting-and-ai-music")
        self.assertNotEqual(skill["source"], "missing")
        self.assertIn("Suno", skill["instructions"])

    def test_openclaw_skill_is_loaded_from_grouped_directory(self):
        skill = load("skill-creator")
        self.assertNotEqual(skill["source"], "missing")
        self.assertIn("Skill Creator", skill["instructions"])

    def test_invoke_uses_skill_and_provider(self):
        result = router.invoke("songwriting-ai-music", "Сделай короткий припев")
        self.assertTrue(result["ok"])
        self.assertEqual(result["answer"], "TEST_OK")
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["skill"], "songwriting-and-ai-music")
        self.assertTrue(self.fake.calls)
        prompt = self.fake.calls[0][1][-1]["content"][0]["text"]
        self.assertIn("Сделай короткий припев", prompt)
        self.assertIn("SØNA SKILL INSTRUCTIONS", prompt)

    def test_invoke_routes_configured_tools_to_provider(self):
        result = router.invoke(
            "assistant",
            "Проанализируй текущие результаты микса и дай рекомендации",
            context={"analysis": {"crest_factor_db": 6.0}},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["answer"], "TEST_TOOL_OK")
        self.assertEqual(result["tool_calls"], [{"name": "music.analyze_mix", "status": "ok"}])
        exposed = {tool["name"] for tool in self.fake.tool_calls[-1]}
        self.assertEqual(exposed, {"music.analyze_mix", "music.build_advice"})
        self.assertIn("problems", self.fake.last_tool_result)

    def test_unconfigured_agent_keeps_legacy_provider_path(self):
        result = router.invoke("songwriter", "Напиши хук")
        self.assertTrue(result["ok"])
        self.assertNotIn("tool_calls", result)
        self.assertEqual(result["answer"], "TEST_OK")

    def test_music_tool_schema_is_responses_compatible(self):
        specs = get_tool_specs(["music.analyze_mix", "music.build_advice"])
        self.assertEqual({item["type"] for item in specs}, {"function"})
        self.assertTrue(all(item["strict"] for item in specs))
        self.assertTrue(all("parameters" in item for item in specs))

    def test_invoke_supports_prompts_chat_provider(self):
        original_search = router.search_prompts
        router.search_prompts = lambda message, limit=4: [
            {"id": "test-1", "title": "Prompt", "description": "test", "content": "example"}
        ]
        try:
            result = router.invoke("prompt-engineering", "Улучши промпт для вокала")
        finally:
            router.search_prompts = original_search

        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "openai+prompts.chat")
        self.assertEqual(result["sources"][0]["id"], "test-1")
        prompt = self.fake.calls[-1][1][-1]["content"][0]["text"]
        self.assertIn("UNTRUSTED PROMPTS.CHAT REFERENCES", prompt)

    def test_music_tools_are_registered(self):
        names = {item["name"] for item in list_tools()}
        self.assertIn("music.analyze_mix", names)
        self.assertIn("music.build_advice", names)

    def test_music_analyze_tool_executes_existing_engine(self):
        result = execute_tool(
            "music.analyze_mix",
            {
                "analysis": {
                    "crest_factor_db": 6.0,
                    "true_peak_dbfs": -0.2,
                    "mono_correlation": 0.1,
                },
                "decisions": [],
                "master_report": {},
            },
        )
        self.assertIn("problems", result)
        self.assertTrue(result["problems"])
        self.assertEqual(result["problems"][0]["severity"], "high")

    def test_unknown_tool_is_rejected(self):
        with self.assertRaises(ToolError):
            execute_tool("python.exec", {})

    def test_unknown_configured_tool_is_rejected(self):
        with self.assertRaises(ToolError):
            get_tool_specs(["python.exec"])

    def test_unknown_agent_is_rejected(self):
        with self.assertRaises(router.AgentError):
            router.invoke("does-not-exist", "test")

    def test_empty_message_is_rejected(self):
        with self.assertRaises(router.AgentError):
            router.invoke("assistant", "   ")


if __name__ == "__main__":
    unittest.main()
