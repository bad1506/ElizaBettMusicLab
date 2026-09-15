import os
import tempfile
import unittest
from pathlib import Path
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
        available = {tool["name"] for tool in tools}
        if "music.get_current_intelligence_report" in available:
            result = execute_tool("music.get_current_intelligence_report", {})
            called_name = "music.get_current_intelligence_report"
        elif "music.get_current_analysis" in available:
            result = execute_tool("music.get_current_analysis", {})
            called_name = "music.get_current_analysis"
        else:
            result = execute_tool("music.analyze_mix", {"analysis": {"crest_factor_db": 6.0}, "decisions": [], "master_report": {}})
            called_name = "music.analyze_mix"
        self.last_tool_result = result
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

    def test_registry_and_skills(self):
        agents = router.list_agents()
        for name in ("assistant", "songwriter", "songwriting-ai-music", "skill-creator"):
            self.assertIn(name, agents)
        self.assertTrue(agents["skill-creator"]["enabled"])
        self.assertEqual(agents["skill-creator"]["source"], "openclaw")
        for agent_name, spec in agents.items():
            skill = load(spec["skill"])
            self.assertNotEqual(skill["source"], "missing", agent_name)
            self.assertTrue(skill["instructions"].strip())

    def test_invoke_uses_skill_and_tools(self):
        result = router.invoke("songwriting-ai-music", "Сделай короткий припев")
        self.assertTrue(result["ok"])
        self.assertEqual(result["answer"], "TEST_TOOL_OK")
        self.assertEqual(result["skill"], "songwriting-and-ai-music")
        self.assertIn("SØNA SKILL INSTRUCTIONS", self.fake.calls[0][1][-1]["content"][0]["text"])

    def test_agent_prefers_unified_music_intelligence_report(self):
        result = router.invoke("assistant", "Проанализируй мой трек целиком")
        self.assertTrue(result["ok"])
        self.assertEqual(result["tool_calls"][0]["name"], "music.get_current_intelligence_report")
        system = self.fake.calls[-1][0]
        self.assertIn("СНАЧАЛА используй music.get_current_intelligence_report", system)
        self.assertIn("Не вызывай несколько отдельных", system)

    def test_all_music_tools_are_exposed(self):
        result = router.invoke("assistant", "Проанализируй текущий трек")
        self.assertTrue(result["ok"])
        exposed = {tool["name"] for tool in self.fake.tool_calls[-1]}
        self.assertEqual(exposed, {
            "music.get_current_analysis", "music.get_current_timeline", "music.get_current_intelligence",
            "music.get_current_vocal_context", "music.get_current_melody_map", "music.get_current_intelligence_report",
            "music.diagnose_vocal_in_section", "music.analyze_mix", "music.build_advice",
        })

    @patch("agents.tools.music.current_analysis")
    def test_current_analysis_tool(self, mocked):
        mocked.return_value = {"status": "ok", "file": "track.wav", "analysis": {"timeline": {}, "intelligence": {}}}
        result = execute_tool("music.get_current_analysis", {})
        self.assertEqual(result["file"], "track.wav")
        mocked.assert_called_once()

    @patch("agents.tools.music.current_analysis", return_value=None)
    def test_current_analysis_missing_audio(self, mocked):
        result = execute_tool("music.get_current_analysis", {})
        self.assertEqual(result["status"], "no_audio")
        mocked.assert_called_once()

    @patch("agents.tools.music.current_music_intelligence", return_value={"status": "no_audio", "message": "У текущего пользователя нет доступного аудиофайла для анализа."})
    def test_unified_intelligence_report_no_audio(self, mocked):
        result = execute_tool("music.get_current_intelligence_report", {})
        self.assertEqual(result["status"], "no_audio")
        mocked.assert_called_once_with()

    @patch("agents.tools.registry.current_music_intelligence")
    def test_unified_intelligence_report_registered(self, mocked):
        mocked.return_value = {"status": "ok", "file": "track.wav", "technical": {"bpm": 120}, "structure": {"section_count": 2}, "issues": [], "priority_order": []}
        spec = get_tool_specs(["music.get_current_intelligence_report"])[0]
        self.assertEqual(spec["parameters"]["required"], [])
        result = execute_tool("music.get_current_intelligence_report", {})
        self.assertEqual(result["technical"]["bpm"], 120)
        mocked.assert_called_once_with()

    def test_unified_intelligence_report_composes_cached_snapshot(self):
        from agents.music_context import clear_music_snapshot_cache, current_music_intelligence
        clear_music_snapshot_cache()
        snapshot = {
            "status": "ok",
            "file": "track.wav",
            "analysis": {"decisions": [{"issue": "masking", "severity": "high", "recommendation": "Сделать dynamic EQ"}], "processing_plan": []},
            "audio_context": {"duration": 180, "tempo": {"bpm": 124}, "key": {"name": "A minor"}, "sections": [{"index": 1, "start": 0, "end": 30, "role_hint": "verse", "energy_db_relative": 0}]},
            "intelligence": {"spectral": {}, "stereo": {}, "transients": {}, "vocal_events": {}},
            "timeline": {"loudness": {"segments": []}},
            "melody_map": {"events": []},
        }
        with patch("agents.music_context._latest_audio", return_value=Path("/tmp/track.wav")), patch("agents.music_context._get_music_snapshot", return_value=snapshot) as snapshot_mock:
            result = current_music_intelligence()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["file"], "track.wav")
        self.assertEqual(result["technical"]["duration_sec"], 180.0)
        self.assertEqual(result["technical"]["bpm"], 124.0)
        self.assertEqual(result["technical"]["key"], "A minor")
        self.assertEqual(result["structure"]["section_count"], 1)
        self.assertEqual(result["issues"][0]["severity"], "high")
        self.assertEqual(result["priority_order"], ["Сделать dynamic EQ"])
        snapshot_mock.assert_called_once()

    def _mock_audio_snapshot(self, user_id="user-1"):
        from agents.music_context import clear_music_snapshot_cache
        clear_music_snapshot_cache()
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name) / "track.wav"
        path.write_bytes(b"audio-v1")
        self.addCleanup(tmp.cleanup)
        analysis = {"decisions": [], "processing_plan": []}
        audio = {"duration": 180, "tempo": {"bpm": 124}, "key": {"name": "A minor"}, "sections": []}
        intelligence = {"spectral": {}, "stereo": {}, "transients": {}, "vocal_events": {}}
        timeline = {"loudness": {"segments": []}}
        melody = {"events": []}
        patches = [
            patch("agents.music_context._latest_audio", return_value=path),
            patch("security.current_user_id", return_value=user_id),
            patch("master_engine.analyze_file", return_value=analysis),
            patch("audio_to_song.analyze", return_value=audio),
            patch("audio_intelligence.analyze_audio", return_value=intelligence),
            patch("audio_timeline.build_timeline", return_value=timeline),
            patch("melody_alignment.analyze", return_value=melody),
        ]
        mocks = [item.start() for item in patches]
        for item in patches:
            self.addCleanup(item.stop)
        return path, mocks

    def test_music_snapshot_cache_hits_across_unified_and_specialized_reads(self):
        from agents.music_context import current_intelligence, current_music_intelligence, current_melody_map, current_timeline, current_vocal_context
        _, mocks = self._mock_audio_snapshot()
        current_music_intelligence()
        current_timeline()
        current_intelligence()
        current_vocal_context()
        current_melody_map()
        current_music_intelligence()
        for mocked in mocks[2:]:
            self.assertEqual(mocked.call_count, 1)

    def test_music_snapshot_cache_invalidates_when_audio_changes(self):
        from agents.music_context import current_music_intelligence
        path, mocks = self._mock_audio_snapshot()
        current_music_intelligence()
        for mocked in mocks[2:]:
            self.assertEqual(mocked.call_count, 1)
        path.write_bytes(b"audio-v2-with-new-size")
        os.utime(path, None)
        current_music_intelligence()
        for mocked in mocks[2:]:
            self.assertEqual(mocked.call_count, 2)

    def test_music_snapshot_cache_isolated_between_users(self):
        from agents.music_context import current_music_intelligence
        _, mocks = self._mock_audio_snapshot(user_id="user-1")
        current_music_intelligence()
        with patch("security.current_user_id", return_value="user-2"):
            current_music_intelligence()
        for mocked in mocks[2:]:
            self.assertEqual(mocked.call_count, 2)

    def test_clear_music_snapshot_cache_is_scoped_to_user(self):
        from agents.music_context import clear_music_snapshot_cache, current_music_intelligence
        _, mocks = self._mock_audio_snapshot(user_id="user-1")
        current_music_intelligence()
        with patch("security.current_user_id", return_value="user-2"):
            current_music_intelligence()
        clear_music_snapshot_cache("user-1")
        current_music_intelligence()
        for mocked in mocks[2:]:
            self.assertEqual(mocked.call_count, 3)

    def test_specialized_tools_registered(self):
        names = {item["name"] for item in list_tools()}
        self.assertTrue({
            "music.get_current_timeline", "music.get_current_intelligence", "music.get_current_vocal_context",
            "music.get_current_melody_map", "music.diagnose_vocal_in_section", "music.get_current_intelligence_report",
        }.issubset(names))

    @patch("agents.tools.music.current_vocal_context")
    @patch("agents.tools.music.current_analysis")
    def test_vocal_diagnosis_auto_selects_chorus(self, analysis_mock, context_mock):
        context_mock.return_value = {"status": "ok", "file": "track.wav", "audio_context": {"sections": [
            {"index": 1, "start": 0, "end": 8, "energy_db_relative": -2, "energy_label": "MID ENERGY", "role_hint": "intro/verse candidate"},
            {"index": 2, "start": 8, "end": 20, "energy_db_relative": 5, "energy_label": "HIGH ENERGY", "role_hint": "likely chorus/drop candidate"},
        ]}}
        analysis_mock.return_value = {
            "status": "ok", "file": "track.wav", "analysis": {
                "timeline": {"loudness": {"segments": [{"start": 0, "end": 8, "lufs": -14}, {"start": 8, "end": 13, "lufs": -10}, {"start": 13, "end": 20, "lufs": -10}]}},
                "intelligence": {
                    "spectral": {"segments": [
                        {"start": 0, "end": 8, "centroid_hz": 1500, "rolloff_hz": 7000, "bands": {"low_mid": 18, "presence": 30, "mid": 24, "bass": 18}},
                        {"start": 8, "end": 13, "centroid_hz": 1400, "rolloff_hz": 6800, "bands": {"low_mid": 24, "presence": 28, "mid": 25, "bass": 20}},
                        {"start": 13, "end": 20, "centroid_hz": 1400, "rolloff_hz": 6800, "bands": {"low_mid": 24, "presence": 28, "mid": 25, "bass": 20}},
                    ]},
                    "stereo": {"segments": [{"start": 8, "end": 13, "correlation": 0.75}, {"start": 13, "end": 20, "correlation": 0.75}]},
                    "transients": {"events": [{"start": 8, "end": 20, "count": 4}]},
                    "vocal_events": {"events": [{"start": 8, "end": 20, "voiced_percent": 72}]},
                },
            },
        }
        result = execute_tool("music.diagnose_vocal_in_section", {})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["section"]["start_sec"], 8.0)
        self.assertEqual(result["section"]["end_sec"], 20.0)
        self.assertEqual(result["section_selection"]["mode"], "automatic")
        self.assertEqual(result["section_selection"]["selected_index"], 2)
        self.assertTrue(any(item["cause"] == "low_mid_masking" for item in result["diagnosis"]))
        context_mock.assert_called_once()
        analysis_mock.assert_called_once()

    @patch("agents.tools.music.current_vocal_context")
    def test_vocal_diagnosis_selects_named_section(self, context_mock):
        context_mock.return_value = {"audio_context": {"sections": [
            {"index": 1, "start": 0, "end": 7, "energy_db_relative": 0, "role_hint": "intro/verse candidate"},
            {"index": 2, "start": 7, "end": 15, "energy_db_relative": 3, "role_hint": "bridge candidate"},
        ]}}
        with patch("agents.tools.music.current_analysis", return_value=None):
            result = execute_tool("music.diagnose_vocal_in_section", {"section_name": "bridge"})
        self.assertEqual(result["status"], "no_audio")
        self.assertEqual(result["message"], "У текущего пользователя нет доступного аудиофайла для анализа.")

    def test_diagnostic_schema_allows_automatic_selection(self):
        spec = next(item for item in get_tool_specs(["music.diagnose_vocal_in_section"]) if item["name"] == "music.diagnose_vocal_in_section")
        self.assertEqual(spec["parameters"]["required"], [])
        self.assertEqual(set(spec["parameters"]["properties"]), {"section_start_sec", "section_end_sec", "section_name"})

    @patch("agents.tools.music.current_timeline", return_value={"status": "ok", "file": "track.wav", "loudness": {"segments": []}})
    def test_timeline_tool(self, mocked):
        self.assertEqual(execute_tool("music.get_current_timeline", {})["file"], "track.wav")
        mocked.assert_called_once()

    @patch("agents.tools.music.current_intelligence", return_value={"status": "ok", "file": "track.wav"})
    def test_intelligence_tool(self, mocked):
        self.assertEqual(execute_tool("music.get_current_intelligence", {})["status"], "ok")
        mocked.assert_called_once()

    @patch("agents.tools.music.current_vocal_context", return_value={"status": "ok", "file": "track.wav", "audio_context": {"sections": []}})
    def test_vocal_context_tool(self, mocked):
        self.assertEqual(execute_tool("music.get_current_vocal_context", {})["file"], "track.wav")
        mocked.assert_called_once()

    @patch("agents.tools.music.current_melody_map", return_value={"status": "ok", "file": "track.wav", "melody_map": {"events": []}})
    def test_melody_map_tool(self, mocked):
        self.assertEqual(execute_tool("music.get_current_melody_map", {})["file"], "track.wav")
        mocked.assert_called_once()

    def test_legacy_provider_path_for_agent_without_tools(self):
        result = router.invoke("release-marketing", "Напиши пост")
        self.assertTrue(result["ok"])
        self.assertEqual(result["answer"], "TEST_OK")
        self.assertNotIn("tool_calls", result)

    def test_unknown_tool_and_agent_are_rejected(self):
        with self.assertRaises(ToolError):
            execute_tool("python.exec", {})
        with self.assertRaises(router.AgentError):
            router.invoke("does-not-exist", "test")
        with self.assertRaises(router.AgentError):
            router.invoke("assistant", "   ")

    def test_analyze_mix_existing_engine(self):
        result = execute_tool("music.analyze_mix", {"analysis": {"crest_factor_db": 6.0, "true_peak_dbfs": -0.2, "mono_correlation": 0.1}, "decisions": [], "master_report": {}})
        self.assertTrue(result["problems"])
        self.assertEqual(result["problems"][0]["severity"], "high")


if __name__ == "__main__":
    unittest.main()
