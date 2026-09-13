from __future__ import annotations
from pathlib import Path
from typing import Any
import numpy as np
import librosa

VERSION = "6.8"


def _load(path: Path):
    y, sr = librosa.load(str(path), sr=None, mono=True)
    y = np.asarray(y, dtype=np.float32)
    return y, int(sr)


def _key_from_chroma(y: np.ndarray, sr: int) -> dict[str, Any]:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=2048)
    profile = np.mean(chroma, axis=1)
    # Krumhansl-style major/minor templates; this is an estimate, not symbolic transcription.
    major = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    def score(template, shift):
        t = np.roll(template, shift)
        return float(np.corrcoef(profile, t)[0, 1]) if np.std(profile) > 1e-9 else 0.0
    candidates = [(score(major, i), names[i], "major") for i in range(12)] + [(score(minor, i), names[i], "minor") for i in range(12)]
    candidates.sort(reverse=True)
    best = candidates[0]
    margin = best[0] - candidates[1][0]
    return {"key": f"{best[1]} {best[2]}", "root": best[1], "mode": best[2], "confidence": round(float(np.clip((best[0] + 1) * 50 + margin * 80, 0, 99)), 1), "method": "CQT chroma template estimate"}


def _tempo(y: np.ndarray, sr: int) -> dict[str, Any]:
    onset = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset, units="time")
    bpm = float(np.asarray(tempo).reshape(-1)[0]) if np.size(tempo) else 0.0
    # Common double/half tempo alternatives are useful for songwriting, but the detected value remains primary.
    alts = sorted({round(bpm, 1), round(bpm * 2, 1), round(bpm / 2, 1)}) if bpm > 0 else []
    return {"bpm": round(bpm, 2), "beat_count": int(len(beats)), "beat_times": [round(float(x), 3) for x in beats[:600]], "alternatives_bpm": alts, "confidence": round(float(np.clip(len(beats) / max(len(y) / sr * max(bpm, 1) / 60, 1), 0, 1) * 100), 1)}


def _sections(y: np.ndarray, sr: int, beats: np.ndarray) -> list[dict[str, Any]]:
    duration = len(y) / sr
    hop = 2048
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    rms_db = librosa.amplitude_to_db(rms + 1e-9, ref=np.max)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
    # Structural novelty: spectral flux + harmonic/chroma change.
    flux = np.maximum(0, np.diff(rms_db, prepend=rms_db[:1]))
    chroma_delta = np.mean(np.abs(np.diff(chroma, axis=1, prepend=chroma[:, :1])), axis=0)
    novelty = librosa.util.normalize(0.45 * librosa.util.normalize(flux) + 0.55 * librosa.util.normalize(chroma_delta))
    distance = max(8.0, duration / 12.0)
    frames = librosa.util.peak_pick(novelty, pre_max=3, post_max=3, pre_avg=3, post_avg=3, delta=0.12, wait=int(distance * sr / hop))
    times = librosa.frames_to_time(frames, sr=sr, hop_length=hop)
    boundaries = [0.0] + [float(t) for t in times if 4 < t < duration - 4]
    # Prefer a compact number of section candidates for lyric planning.
    boundaries = sorted(set(round(x, 2) for x in boundaries))
    if len(boundaries) > 11:
        idx = np.linspace(0, len(boundaries) - 1, 11).round().astype(int)
        boundaries = [boundaries[i] for i in idx]
    boundaries.append(round(duration, 2))
    sections = []
    med = float(np.median(rms_db)) if len(rms_db) else 0.0
    for i in range(len(boundaries) - 1):
        start, end = boundaries[i], boundaries[i + 1]
        mask = (np.arange(len(rms_db)) * hop / sr >= start) & (np.arange(len(rms_db)) * hop / sr < end)
        energy = float(np.mean(rms_db[mask])) if np.any(mask) else med
        rel = energy - med
        label = "HIGH ENERGY" if rel > 3 else "LOW ENERGY" if rel < -3 else "MID ENERGY"
        sections.append({"index": i + 1, "start": start, "end": end, "duration": round(end - start, 2), "energy_db_relative": round(rel, 2), "energy_label": label})
    # Give the Director useful arrangement hypotheses without pretending these are certain labels.
    if sections:
        max_i = int(np.argmax([s["energy_db_relative"] for s in sections]))
        sections[max_i]["role_hint"] = "likely chorus/drop candidate"
        sections[0]["role_hint"] = "intro/verse candidate"
        if len(sections) > 2:
            sections[-1]["role_hint"] = "outro/final section candidate"
    return sections


def _vocal_activity(y: np.ndarray, sr: int, segment_sec: float = 4.0) -> list[dict[str, Any]]:
    target = 22050 if sr > 22050 else sr
    yy = librosa.resample(y, orig_sr=sr, target_sr=target) if sr != target else y
    hop = 512
    try:
        f0, voiced, prob = librosa.pyin(yy, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C6"), sr=target, frame_length=2048, hop_length=hop)
    except Exception:
        return []
    times = librosa.frames_to_time(np.arange(len(f0)), sr=target, hop_length=hop)
    valid = np.isfinite(f0) & (prob > 0.55)
    duration = len(yy) / target
    out = []
    for start in np.arange(0, duration, segment_sec):
        end = min(duration, start + segment_sec)
        mask = valid & (times >= start) & (times < end)
        out.append({"start": round(float(start), 2), "end": round(float(end), 2), "voiced_percent": round(float(np.mean(mask) * 100), 1), "active": bool(np.mean(mask) > 0.18)})
    return out


def analyze(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    y, sr = _load(path)
    duration = len(y) / sr
    tempo = _tempo(y, sr)
    key = _key_from_chroma(y, sr)
    beats = np.asarray(tempo["beat_times"], dtype=float)
    sections = _sections(y, sr, beats)
    vocal = _vocal_activity(y, sr)
    rms = librosa.feature.rms(y=y, hop_length=2048)[0]
    energy = librosa.amplitude_to_db(rms + 1e-9, ref=np.max)
    return {
        "version": VERSION,
        "duration_sec": round(duration, 3),
        "tempo": tempo,
        "key": key,
        "sections": sections,
        "vocal_activity": vocal,
        "global_energy": {"min_db_rel": round(float(np.min(energy)), 2), "median_db_rel": round(float(np.median(energy)), 2), "max_db_rel": round(float(np.max(energy)), 2)},
        "confidence": {"tempo": tempo["confidence"], "key": key["confidence"], "structure": round(float(np.clip(len(sections) * 8, 0, 80)), 1)},
        "method_notes": [
            "BPM uses onset-strength beat tracking.",
            "Key uses CQT chroma template matching and is an estimate, not guaranteed ground truth.",
            "Sections are candidate boundaries from novelty/energy changes; role labels are hypotheses.",
            "Vocal activity is full-mix monophonic pitch activity, not isolated-vocal transcription.",
        ],
    }
