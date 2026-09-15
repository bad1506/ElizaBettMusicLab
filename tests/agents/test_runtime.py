import unittest
from unittest.mock import patch

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
        available = {tool["name"] for tool in tools}
        if "music.get_current_analysis" in available:
            result = execute_tool("music.get_current_analysis", {})
            self.last_tool_result = result
            called_name = "music.get_current_analysis"
        else:
            result = execute_tool("music.analyze_mix", {"analysis": {"crest_factor_db": 6.0}, "decisions": [], "master_report": {}})
            self.last_tool_result = result
            called_name = "music.analyze_mix"
        self.tool_call_name = called_name
        return "TEST_TOOL_OK", [{"name": called_name, "status": "ok"}]


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
        for agent_name, spec in router.list_agents().items():
            skill_name = spec.get("skill")
            self.assertIsInstance(skill_name, str, agent_name)
            skill = load(skill_name)
            self.assertNotEqual(skill["source"], "missing", f"Agent {agent_name!r} points to missing skill {skill_name!r}")
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
        self.assertEqual(result["answer"], "TEST_TOOL_OK")
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["skill"], "songwriting-and-ai-music")
        self.assertTrue(self.fake.calls)
        prompt = self.fake.calls[0][1][-1]["content"][0]["text"]
        self.assertIn("Сделай короткий припев", prompt)
        self.assertIn("SØNA SKILL INSTRUCTIONS", prompt)

    def test_invoke_routes_configured_tools_to_provider(self):
        result = router.invoke("assistant", "Проанализируй текущие результаты микса и дай рекомендации", context={"analysis": {"crest_factor_db": 6.0}})
        self.assertTrue(result["ok"])
        self.assertEqual(result["answer"], "TEST_TOOL_OK")
        self.assertEqual(result["tool_calls"], [{"name": "music.get_current_analysis", "status": "ok"}])
        exposed = {tool["name"] for tool in self.fake.tool_calls[-1]}
        self.assertIn("music.diagnose_vocal_in_section", exposed)
        self.assertEqual(self.fake.last_tool_result["status"], "no_audio")

    @patch("agents.tools.music.current_analysis")
    def test_current_analysis_tool_returns_latest_analysis(self, current_analysis_mock):
        current_analysis_mock.return_value = {"status": "ok", "file": "track.wav", "analysis": {"timeline": {"segments": [{"start": 0, "end": 5}]}, "intelligence": {"findings": []}, "decisions": [], "master_brain": {"summary": "test"}}}
        result = execute_tool("music.get_current_analysis", {})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["file"], "track.wav")
        self.assertIn("timeline", result["analysis"])
        current_analysis_mock.assert_called_once()

    @patch("agents.tools.music.current_analysis", return_value=None)
    def test_current_analysis_tool_handles_missing_audio(self, current_analysis_mock):
        result = execute_tool("music.get_current_analysis", {})
        self.assertEqual(result["status"], "no_audio")
        current_analysis_mock.assert_called_once()

    def test_specialized_music_tools_are_read_only_and_registered(self):
        names = {item["name"] for item in list_tools()}
        expected = {"music.get_current_timeline", "music.get_current_intelligence", "music.get_current_vocal_context", "music.get_current_melody_map", "music.diagnose_vocal_in_section"}
        self.assertTrue(expected.issubset(names))

    @patch("agents.tools.music.current_timeline", return_value={"status": "ok", "file": "track.wav", "loudness": {"segments": []}})
    def test_current_timeline_tool(self, mocked):
        result = execute_tool("music.get_current_timeline", {})
        self.assertEqual(result["file"], "track.wav")
        self.assertIn("loudness", result)
        mocked.assert_called_once()

    @patch("agents.tools.music.current_intelligence", return_value={"status": "ok", "file": "track.wav", "findings": []})
    def test_current_intelligence_tool(self, mocked):
        result = execute_tool("music.get_current_intelligence", {})
        self.assertEqual(result["status"], "ok")
        mocked.assert_called_once()

    @patch("agents.tools.music.current_vocal_context", return_value={"status": "ok", "file": "track.wav", "audio_context": {"sections": []}})
    def test_current_vocal_context_tool(self, mocked):
        result = execute_tool("music.get_current_vocal_context", {})
        self.assertEqual(result["file"], "track.wav")
        self.assertIn("audio_context", result)
        mocked.assert_called_once()

    @patch("agents.tools.music.current_melody_map", return_value={"status": "ok", "file": "track.wav", "melody_map": {"events": []}})
    def test_current_melody_map_tool(self, mocked):
        result = execute_tool("music.get_current_melody_map", {})
        self.assertEqual(result["file"], "track.wav")
        self.assertIn("melody_map", result)
        mocked.assert_called_once()

    @patch("agents.tools.music.current_analysis")
    def test_vocal_section_diagnostic_finds_low_mid_masking(self, current_analysis_mock):
        current_analysis_mock.return_value = {
            "status": "ok",
            "file": "track.wav",
            "analysis": {
                "timeline": {"loudness": {"segments": [
                    {"start": 0, "end": 5, "lufs": -12}, {"start": 5, "end": 10, "lufs": -10},
                ]}},
                "intelligence": {
                    "spectral": {"segments": [
                        {"start": 0, "end": 5, "centroid_hz": 1500, "rolloff_hz": 7000, "bands": {"low_mid": 18, "presence": 28, "mid": 25, "bass": 20}},
                        {"start": 5, "end": 10, "centroid_hz": 1400, "rolloff_hz": 6800, "bands": {"low_mid": 24, "presence": 28, "mid": 25, "bass": 20}},
                    ]},
                    "stereo": {"segments": [
                        {"start": 0, "end": 5, "correlation": 0.8}, {"start": 5, "end": 10, "correlation": 0.75},
                    ]},
                    "transients": {"events": [
                        {"start": 5, "end": 10, "count": 4},
                    ]},
                    "vocal_events": {"events": [
                        {"start": 5, "end": 10, "voiced_percent": 72, "median_midi": 64, "pitch_drift": 0.1},
                    ]},
                },
            },
        }
        result = execute_tool("music.diagnose_vocal_in_section", {"section_start_sec": 5, "section_end_sec": 10})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["section"]["start_sec"], 5.0)
        self.assertTrue(any(item["cause"] == "low_mid_masking" for item in result["diagnosis"]))
        self.assertEqual(result["vocal"]["median_voiced_percent"], 72.0)
        current_analysis_mock.assert_called_once()

    @patch("agents.tools.music.current_analysis", return_value=None)
    def test_vocal_section_diagnostic_handles_missing_audio(self, current_analysis_mock):
        result = execute_tool("music.diagnose_vocal_in_section", {"section_start_sec": 5, "section_end_sec": 10})
        self.assertEqual(result["status"], "no_audio")
        current_analysis_mock.assert_called_once()

    def test_vocal_section_diagnostic_rejects_invalid_window(self):
        with self.assertRaises(ToolError):
            execute_tool("music.diagnose_vocal_in_section", {"section_start_sec": 10, "section_end_sec": 5})
        with self.assertRaises(ToolError):
            execute_tool("music.diagnose_vocal_in_section", {"section_start_sec": 0, "section_end_sec": 121})

    def test_tool_enabled_agent_does_not_preload_expensive_analysis(self):
        with patch("agents.router.current_analysis", side_effect=AssertionError("router must not preload analysis"), create=True):
            result = router.invoke("assistant", "Что можешь сделать?")
        self.assertTrue(result["ok"])
        self.assertEqual(result["answer"], "TEST_TOOL_OK")

    def test_unconfigured_agent_keeps_legacy_provider_path(self):
        result = router.invoke("songwriter", "Напиши хук")
        self.assertTrue(result["ok"])
        self.assertNotIn("tool_calls", result)
        self.assertEqual(result["answer"], "TEST_OK")

    def test_music_tool_schema_is_responses_compatible(self):
        names = ["music.get_current_analysis", "music.get_current_timeline", "music.get_current_intelligence", "music.get_current_vocal_context", "music.get_current_melody_map", "music.diagnose_vocal_in_section", "music.analyze_mix", "music.build_advice"]
        specs = get_tool_specs(names)
        self.assertEqual({item["type"] for item in specs}, {"function"})
        self.assertTrue(all(item["strict"] for item in specs))
        current = next(item for item in specs if item["name"] == "music.diagnose_vocal_in_section")
        self.assertEqual(set(current["parameters"]["required"]), {"section_start_sec", "section_end_sec"})
        self.assertEqual(current["parameters"]["properties"]["section_start_sec"]["type"], "number")

    def test_invoke_supports_prompts_chat_provider(self):
        original_search = router.search_prompts
        router.search_prompts = lambda message, limit=4: [{"id": "test-1", "title": "Prompt", "description": "test", "content": "example"}]
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
        self.assertIn("music.get_current_analysis", names)
        self.assertIn("music.analyze_mix", names)
        self.assertIn("music.build_advice", names)
        self.assertIn("music.diagnose_vocal_in_section", names)

    def test_music_analyze_tool_executes_existing_engine(self):
        result = execute_tool("music.analyze_mix", {"analysis": {"crest_factor_db": 6.0, "true_peak_dbfs": -0.2, "mono_correlation": 0.1}, "decisions": [], "master_report": {}})
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
