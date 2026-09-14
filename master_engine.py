from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

import librosa
import numpy as np
import soundfile as sf

import mastering
import processing_executor
import quality_control
from decision_engine import build_decisions
from processing_planner import build_processing_plan
from spectral_timeline import spectral_timeline_analyze
import audio_intelligence
import master_brain

ENGINE_VERSION = "6.5"

MASTER_PROFILES = {
    "latest_auto": {"label": "Latest Auto · Adaptive", "factor": 0.92, "target_lufs": -10.5},
    "suno6_commercial": {"label": "Suno 6 · Commercial", "factor": 0.92, "target_lufs": -10.5},
    "suno55_balanced": {"label": "Suno 5.5 · Balanced", "factor": 0.82, "target_lufs": -11.0},
    "clean_streaming": {"label": "Clean Streaming", "factor": 0.68, "target_lufs": -12.0},
}


def _resolve_input(source: Any) -> Path:
    if isinstance(source, dict):
        source = source.get("file_path") or source.get("input") or source.get("path")
    if source is None:
        raise ValueError("Не указан входной аудиофайл")
    path = Path(str(source)).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Аудиофайл не найден: {path}")
    return path


def analyze_file(source: Any) -> dict[str, Any]:
    path = _resolve_input(source)
    audio, sr = librosa.load(str(path), sr=None, mono=False)
    if audio.ndim == 1:
        audio2 = audio[:, None]
    else:
        audio2 = audio.T
    audio2 = np.asarray(audio2, dtype=np.float64)
    if audio2.shape[1] > 2:
        audio2 = audio2[:, :2]

    adaptive = mastering.adaptive_analyze(audio2, sr)
    timeline = spectral_timeline_analyze(audio2, sr, segment_sec=10.0)
    decisions = build_decisions(timeline)
    plan = build_processing_plan(decisions)
    intelligence = audio_intelligence.analyze_audio(path, segment_sec=5.0)
    brain_input = {"decisions": decisions, "intelligence": intelligence}
    brain = master_brain.build_brain(brain_input)
    return {
        "file": path.name,
        "file_path": str(path),
        "sample_rate": int(sr),
        "duration_sec": round(len(audio2) / sr, 3),
        "adaptive_analysis": adaptive,
        "timeline": timeline,
        "timeline_profile": timeline.get("track_profile", {}),
        "decisions": decisions,
        "processing_plan": plan,
        "intelligence": intelligence,
        "master_brain": brain,
    }


def _auto_target(analysis: dict[str, Any], requested: float) -> tuple[float, str]:
    """Choose a conservative commercial target from dynamics instead of blindly pushing loudness."""
    adaptive = analysis.get("adaptive_analysis", {})
    crest = float(adaptive.get("crest_factor_db", 8.0) or 8.0)
    if crest >= 10.0:
        target = -11.5
        reason = "Высокий динамический запас — сохранена динамика."
    elif crest >= 7.0:
        target = -10.5
        reason = "Сбалансированная динамика — выбран коммерческий target."
    else:
        target = -10.0
        reason = "Плотный исходник — target слегка снижен, чтобы не усиливать артефакты."
    # Respect an explicit non-default target from API callers.
    if requested < -13.0 or requested > -8.0:
        target = float(np.clip(requested, -14.0, -8.0))
        reason = "Использован явно заданный пользователем target LUFS."
    return round(target, 2), reason


def _loudness_score(lufs: float, target: float) -> float:
    error = abs(float(lufs) - float(target))
    return max(0.0, 100.0 - error * 14.0)


def _finalize_loudness(path: Path, target_lufs: float, ceiling_db: float) -> dict[str, Any]:
    audio, sr = sf.read(str(path), always_2d=True)
    audio = np.asarray(audio, dtype=np.float64)
    current = mastering.loudness(audio, sr)
    audio *= mastering.db_to_linear(float(np.clip(target_lufs - current, -6.0, 12.0)))
    for _ in range(8):
        audio = mastering.limiter(audio, ceiling_db=ceiling_db, release_ms=80.0)
        now = mastering.loudness(audio, sr)
        delta = target_lufs - now
        if abs(delta) < 0.04:
            break
        audio *= mastering.db_to_linear(float(np.clip(delta, -0.8, 1.2)))
    audio = mastering.limiter(audio, ceiling_db=ceiling_db, release_ms=80.0)
    audio = np.clip(audio, -1.0, 1.0)
    sf.write(str(path), audio.astype(np.float32), sr, subtype="PCM_24")
    return mastering.analyze_master(audio, sr)


def _candidate_score(qc: dict[str, Any], target_lufs: float) -> float:
    evaluation = qc.get("evaluation", {})
    base = float(evaluation.get("overall_score", 0.0))
    final = qc.get("processed", {})
    loud = _loudness_score(final.get("lufs", target_lufs), target_lufs)
    peak = float(evaluation.get("peak_score", 0.0))
    return round(base * 0.68 + loud * 0.20 + peak * 0.12, 2)


def _candidate_factors(auto_mode: bool = False) -> list[float]:
    """Keep normal runs light; adaptive auto gets a small two-pass comparison."""
    if auto_mode:
        return [0.75, 1.00]
    try:
        count = int(os.getenv("MASTER_MAX_CANDIDATES", "1"))
    except ValueError:
        count = 1
    count = max(1, min(4, count))
    profiles = {1: [1.00], 2: [0.75, 1.00], 3: [0.50, 0.85, 1.00], 4: [0.50, 0.75, 1.00, 1.15]}
    return profiles[count]


def run(source: Any, output_dir: str | Path = "optimizer_output", target_lufs: float = -10.5,
        ceiling_db: float = -1.0, intensity: str = "balanced", reference: Any = None,
        profile: str = "latest_auto") -> dict[str, Any]:
    input_path = _resolve_input(source)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    analysis = analyze_file(input_path)
    base_plan = analysis["processing_plan"]
    auto_mode = profile == "latest_auto" or intensity == "auto"
    profile_cfg = MASTER_PROFILES.get(profile, MASTER_PROFILES["latest_auto"])
    if auto_mode:
        target_lufs, auto_reason = _auto_target(analysis, target_lufs)
        profile_cfg = MASTER_PROFILES["latest_auto"]
    else:
        auto_reason = "Ручной профиль мастеринга."

    effective_factor = float(profile_cfg["factor"])
    factors = _candidate_factors(auto_mode)
    candidates: list[dict[str, Any]] = []

    for factor in factors:
        plan = dict(base_plan)
        plan["steps"] = []
        for step in base_plan.get("steps", []):
            item = dict(step)
            item["gain_db"] = round(float(item.get("gain_db", 0.0)) * factor * effective_factor, 3)
            plan["steps"].append(item)
        plan["steps_count"] = len(plan["steps"])

        name = f"candidate_{str(factor).replace('.', '_')}"
        path = output_dir / f"{input_path.stem}_{name}.wav"
        try:
            processing_executor.execute_processing_plan(input_path, path, plan)
            _finalize_loudness(path, target_lufs, ceiling_db)
            qc = quality_control.compare_files(input_path, path, plan)
            score = _candidate_score(qc, target_lufs)
            verdict = qc.get("evaluation", {}).get("verdict", "unknown")
            candidates.append({"name": name, "factor": factor, "score": score, "verdict": verdict,
                               "output": str(path), "qc": qc, "plan": plan})
        except Exception as exc:
            candidates.append({"name": name, "factor": factor, "score": 0.0,
                               "verdict": "error", "output": None, "error": str(exc)})

    acceptable = [c for c in candidates if c.get("verdict") in {"excellent", "acceptable", "acceptable_with_warnings", "needs_review"}
                  and c.get("score", 0.0) >= 70.0
                  and not any(g.get("status") == "much_worse" for g in c.get("qc", {}).get("evaluation", {}).get("goals", []))]
    acceptable.sort(key=lambda x: x["score"], reverse=True)
    best = acceptable[0] if acceptable else None

    final_path = output_dir / f"{input_path.stem}_MASTER.wav"
    rollback = best is None
    if rollback:
        shutil.copy2(input_path, final_path)
        final_audio, final_sr = sf.read(str(final_path), always_2d=True)
        final_analysis = mastering.analyze_master(final_audio, final_sr)
        selected = {"name": "rollback_original", "factor": 0.0, "score": 0.0, "verdict": "rollback"}
    else:
        shutil.copy2(best["output"], final_path)
        final_audio, final_sr = sf.read(str(final_path), always_2d=True)
        final_analysis = mastering.analyze_master(final_audio, final_sr)
        selected = {k: best.get(k) for k in ("name", "factor", "score", "verdict")}

    reference_report = None
    if reference is not None:
        try:
            ref = analyze_file(reference)
            a = analysis["adaptive_analysis"]
            b = ref["adaptive_analysis"]
            reference_report = {
                "reference_file": ref["file"],
                "lufs_delta": round(float(a.get("lufs", 0) - b.get("lufs", 0)), 3),
                "crest_delta": round(float(a.get("crest_factor_db", 0) - b.get("crest_factor_db", 0)), 3),
                "stereo_width_delta": round(float(a.get("stereo_width_db", 0) - b.get("stereo_width_db", 0)), 3),
                "band_delta": {k: round(float(a.get("band_energy_percent", {}).get(k, 0) - b.get("band_energy_percent", {}).get(k, 0)), 3)
                               for k in a.get("band_energy_percent", {})},
            }
        except Exception as exc:
            reference_report = {"error": str(exc)}

    report = {
        "engine": f"Eliza Bett Music Lab Master Engine {ENGINE_VERSION}",
        "input": str(input_path),
        "final_output": str(final_path),
        "target_lufs": target_lufs,
        "ceiling_db": ceiling_db,
        "intensity": intensity,
        "master_profile": profile_cfg["label"],
        "profile_id": profile,
        "auto_mode": auto_mode,
        "auto_reason": auto_reason,
        "profile_note": "Adaptive commercial mastering; the engine evaluates two safe processing strengths in auto mode and keeps the higher-QC result.",
        "selected_candidate": selected,
        "rollback": rollback,
        "candidate_count": len(factors),
        "analysis": analysis,
        "master_brain": analysis.get("master_brain", {}),
        "candidates": [{k: c.get(k) for k in ("name", "factor", "score", "verdict", "output", "error")} for c in candidates],
        "final_analysis": final_analysis,
        "reference": reference_report,
        "final_intelligence": audio_intelligence.analyze_audio(final_path, segment_sec=5.0),
    }
    report["brain_validation"] = master_brain.compare_intelligence(analysis.get("intelligence", {}), report["final_intelligence"])
    report_path = output_dir / f"{input_path.stem}_MASTER_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
