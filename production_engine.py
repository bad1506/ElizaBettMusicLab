from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import audio_to_song
import melody_alignment
import master_engine
import song_director
import vocal_intelligence
import songwriter_memory

VERSION = "10.0"


def _latest_audio(input_dir: Path) -> Path | None:
    exts = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
    files = [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in exts]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def _compact_audio_context(path: Path) -> dict[str, Any]:
    audio = audio_to_song.analyze(path)
    bpm = (audio.get("tempo") or {}).get("bpm")
    melody = melody_alignment.analyze(path, bpm=bpm)
    vocal = vocal_intelligence.analyze_vocal(path)
    return {"audio_to_song": audio, "melody_map": melody, "vocal": vocal}


def _production_plan(analysis: dict[str, Any], audio_ctx: dict[str, Any], master: dict[str, Any], director: dict[str, Any]) -> dict[str, Any]:
    a = analysis.get("adaptive_analysis") or {}
    decisions = analysis.get("decisions") or []
    audio = audio_ctx.get("audio_to_song") or {}
    melody = audio_ctx.get("melody_map") or {}
    vocal = audio_ctx.get("vocal") or {}
    selected = master.get("selected_candidate") or {}
    return {
        "version": VERSION,
        "principle": "measure → understand → write → produce → master → verify",
        "mix_state": {
            "lufs": a.get("lufs"), "true_peak_dbfs": a.get("true_peak_dbfs"),
            "crest_factor_db": a.get("crest_factor_db"), "mono_correlation": a.get("mono_correlation"),
            "decision_count": len(decisions),
        },
        "music_map": {
            "bpm": (audio.get("tempo") or {}).get("bpm"),
            "bpm_confidence": (audio.get("confidence") or {}).get("tempo"),
            "key": (audio.get("key") or {}).get("key"),
            "key_confidence": (audio.get("key") or {}).get("confidence"),
            "section_count": len(audio.get("sections") or []),
            "melody_phrase_count": melody.get("phrase_count", 0),
            "voiced_ratio": melody.get("voiced_ratio"),
        },
        "vocal_state": {
            "status": vocal.get("status"), "range": vocal.get("range"),
            "pitch_accuracy_percent": vocal.get("pitch_accuracy_percent"),
            "pitch_stability_percent": vocal.get("pitch_stability_percent"),
        },
        "master_state": {
            "rollback": bool(master.get("rollback")),
            "candidate": selected.get("name"), "score": selected.get("score"),
            "final_lufs": (master.get("final_analysis") or {}).get("lufs"),
            "final_true_peak_dbfs": (master.get("final_analysis") or {}).get("true_peak_dbfs"),
        },
        "workflow": [
            {"stage": "ANALYZE", "status": "complete", "detail": f"{len(decisions)} evidence-based decisions"},
            {"stage": "MAP MUSIC", "status": "complete", "detail": f"{len(audio.get('sections') or [])} section candidates · {melody.get('phrase_count', 0)} vocal phrases"},
            {"stage": "DIRECT SONG", "status": director.get("mode", "unknown").lower(), "detail": "creative brief generated from audio + DNA + context"},
            {"stage": "MASTER", "status": "rollback" if master.get("rollback") else "accepted", "detail": selected.get("name", "no candidate")},
            {"stage": "VERIFY", "status": "complete" if master else "pending", "detail": "QC-backed result"},
        ],
        "next_actions": [
            "Use the Director brief as the writing/production source of truth.",
            "Keep lyric density inside the estimated phrase budgets; re-check stresses on the actual melody.",
            "If the master is rolled back, fix the identified mix issue before increasing loudness.",
            "Treat key, BPM, section and phrase labels as estimates unless independently confirmed.",
        ],
    }


def run(input_dir: str | Path, output_dir: str | Path, request: str = "", profile: str = "suno6_commercial", target_lufs: float = -10.5) -> dict[str, Any]:
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = _latest_audio(input_dir)
    if path is None:
        return {"ok": False, "version": VERSION, "status": "no_audio", "message": "Сначала загрузите демо."}

    analysis = master_engine.analyze_file(path)
    audio_ctx = _compact_audio_context(path)
    context = {
        "track": path.name, "profile": profile,
        "analysis": analysis.get("adaptive_analysis", {}),
        "decisions": (analysis.get("decisions") or [])[:12],
        **audio_ctx,
    }
    director = song_director.direct(request, context, "")
    master = master_engine.run(path, output_dir, target_lufs, -1.0, "balanced", reference=None, profile=profile)
    plan = _production_plan(analysis, audio_ctx, master, director)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"{path.stem}_PRODUCTION_{stamp}.json"
    report = {
        "ok": True, "version": VERSION, "created_at": datetime.now(timezone.utc).isoformat(),
        "track": path.name, "request": request, "profile": profile,
        "analysis": analysis, "audio_context": audio_ctx, "director": director,
        "master": master, "production_plan": plan,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    report["report_file"] = report_path.name
    report["report_url"] = f"/files/optimizer_output/{report_path.name}"
    return report
