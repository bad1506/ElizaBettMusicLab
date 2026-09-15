import unittest

from agents import router
from agents.skill_loader import load


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
        router._PROVIDERS["openai"] = self.fake

    def tearDown(self):
        router._PROVIDERS["openai"] = self.original

    def test_registry_contains_existing_and_external_agents(self):
        agents = router.list_agents()
        self.assertIn("assistant", agents)
        self.assertIn("songwriter", agents)
        self.assertIn("songwriting-ai-music", agents)
        self.assertIn("skill-creator", agents)

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

    def test_unknown_agent_is_rejected(self):
        with self.assertRaises(router.AgentError):
            router.invoke("does-not-exist", "test")

    def test_empty_message_is_rejected(self):
        with self.assertRaises(router.AgentError):
            router.invoke("assistant", "   ")


if __name__ == "__main__":
    unittest.main()
