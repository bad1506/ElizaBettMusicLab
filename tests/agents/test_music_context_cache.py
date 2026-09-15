import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agents import music_context


class MusicSnapshotCacheTests(unittest.TestCase):
    def setUp(self):
        music_context.clear_music_snapshot_cache()
        self.tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self.tmp.write(b"audio")
        self.tmp.close()
        self.audio_path = Path(self.tmp.name)

        self.analysis = {"decisions": [], "processing_plan": []}
        self.audio = {
            "duration": 180.0,
            "tempo": {"bpm": 124},
            "key": {"name": "A minor"},
            "sections": [],
        }
        self.intelligence = {"spectral": {}, "stereo": {}, "transients": {}, "vocal_events": {}}
        self.timeline = {"loudness": {"segments": []}}
        self.melody = {"events": []}
        self.calls = {
            "master": 0,
            "audio": 0,
            "intelligence": 0,
            "timeline": 0,
            "melody": 0,
        }

    def tearDown(self):
        music_context.clear_music_snapshot_cache()
        try:
            self.audio_path.unlink()
        except FileNotFoundError:
            pass

    def _modules(self):
        def master(path):
            self.calls["master"] += 1
            return self.analysis

        def audio(path):
            self.calls["audio"] += 1
            return self.audio

        def intelligence(path, segment_sec=5.0):
            self.calls["intelligence"] += 1
            return self.intelligence

        def timeline(path):
            self.calls["timeline"] += 1
            return self.timeline

        def melody(path, bpm=None):
            self.calls["melody"] += 1
            return self.melody

        return {
            "master_engine": SimpleNamespace(analyze_file=master),
            "audio_to_song": SimpleNamespace(analyze=audio),
            "audio_intelligence": SimpleNamespace(analyze_audio=intelligence),
            "audio_timeline": SimpleNamespace(build_timeline=timeline),
            "melody_alignment": SimpleNamespace(analyze=melody),
        }

    def _assert_all_once(self):
        self.assertEqual(self.calls, {
            "master": 1,
            "audio": 1,
            "intelligence": 1,
            "timeline": 1,
            "melody": 1,
        })

    def test_repeated_unified_requests_use_one_snapshot(self):
        modules = self._modules()
        with patch.dict(sys.modules, modules), \
             patch.object(music_context, "_latest_audio", return_value=self.audio_path), \
             patch.object(music_context.security, "current_user_id", return_value="user-1"):
            first = music_context.current_music_intelligence()
            second = music_context.current_music_intelligence()

        self.assertEqual(first["status"], "ok")
        self.assertEqual(second["status"], "ok")
        self._assert_all_once()

    def test_specialized_reads_share_the_same_snapshot(self):
        modules = self._modules()
        with patch.dict(sys.modules, modules), \
             patch.object(music_context, "_latest_audio", return_value=self.audio_path), \
             patch.object(music_context.security, "current_user_id", return_value="user-1"):
            self.assertEqual(music_context.current_analysis()["file"], self.audio_path.name)
            self.assertEqual(music_context.current_timeline()["file"], self.audio_path.name)
            self.assertEqual(music_context.current_intelligence()["file"], self.audio_path.name)
            self.assertEqual(music_context.current_vocal_context()["file"], self.audio_path.name)
            self.assertEqual(music_context.current_melody_map()["file"], self.audio_path.name)

        self._assert_all_once()

    def test_audio_identity_change_rebuilds_snapshot(self):
        modules = self._modules()
        with patch.dict(sys.modules, modules), \
             patch.object(music_context, "_latest_audio", return_value=self.audio_path), \
             patch.object(music_context.security, "current_user_id", return_value="user-1"):
            music_context.current_music_intelligence()
            self.audio_path.write_bytes(b"new-audio-content")
            music_context.current_music_intelligence()

        self.assertEqual(self.calls, {
            "master": 2,
            "audio": 2,
            "intelligence": 2,
            "timeline": 2,
            "melody": 2,
        })

    def test_users_have_isolated_snapshots(self):
        modules = self._modules()
        current_user = {"id": "user-1"}
        with patch.dict(sys.modules, modules), \
             patch.object(music_context, "_latest_audio", return_value=self.audio_path), \
             patch.object(music_context.security, "current_user_id", side_effect=lambda: current_user["id"]):
            music_context.current_music_intelligence()
            current_user["id"] = "user-2"
            music_context.current_music_intelligence()
            current_user["id"] = "user-1"
            music_context.current_music_intelligence()

        self.assertEqual(self.calls, {
            "master": 2,
            "audio": 2,
            "intelligence": 2,
            "timeline": 2,
            "melody": 2,
        })

    def test_clear_cache_is_scoped_to_one_user(self):
        modules = self._modules()
        current_user = {"id": "user-1"}
        with patch.dict(sys.modules, modules), \
             patch.object(music_context, "_latest_audio", return_value=self.audio_path), \
             patch.object(music_context.security, "current_user_id", side_effect=lambda: current_user["id"]):
            music_context.current_music_intelligence()
            current_user["id"] = "user-2"
            music_context.current_music_intelligence()

            music_context.clear_music_snapshot_cache("user-1")
            current_user["id"] = "user-1"
            music_context.current_music_intelligence()
            current_user["id"] = "user-2"
            music_context.current_music_intelligence()

        self.assertEqual(self.calls, {
            "master": 3,
            "audio": 3,
            "intelligence": 3,
            "timeline": 3,
            "melody": 3,
        })

    def test_no_audio_does_not_use_stale_snapshot(self):
        modules = self._modules()
        with patch.dict(sys.modules, modules), \
             patch.object(music_context, "_latest_audio", return_value=self.audio_path), \
             patch.object(music_context.security, "current_user_id", return_value="user-1"):
            music_context.current_music_intelligence()

            with patch.object(music_context, "_latest_audio", return_value=None):
                result = music_context.current_music_intelligence()

        self.assertEqual(result["status"], "no_audio")
        self._assert_all_once()


if __name__ == "__main__":
    unittest.main()
