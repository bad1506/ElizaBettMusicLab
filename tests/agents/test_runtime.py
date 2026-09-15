import unittest

from agents import router
from agents.skill_loader import load
from agents.tools import execute_tool, list_tools
from agents.tools.base import ToolError


class FakeProvider:
    def __init__(self):
        self.calls = []

    def generate(self, *, system, messages):
        self.calls.append((system, messages))
        return "TEST_OK"


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

    def test_unknown_agent_is_rejected(self):
        with self.assertRaises(router.AgentError):
            router.invoke("does-not-exist", "test")

    def test_empty_message_is_rejected(self):
        with self.assertRaises(router.AgentError):
            router.invoke("assistant", "   ")


if __name__ == "__main__":
    unittest.main()
