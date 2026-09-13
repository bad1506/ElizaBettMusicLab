from __future__ import annotations

from pathlib import Path
from typing import Any

import librosa
import numpy as np


def _db(x: float, floor: float = 1e-12) -> float:
    return float(20.0 * np.log10(max(float(x), floor)))


def _load(path: Path) -> tuple[np.ndarray, int]:
    y, sr = librosa.load(str(path), sr=None, mono=False)
    y = np.asarray(y, dtype=np.float32)
    if y.ndim == 1:
        y = y[None, :]
    if y.shape[0] > 2:
        y = y[:2]
    return y, int(sr)


def _band_energy_db(spec: np.ndarray, freqs: np.ndarray, lo: float, hi: float) -> float:
    mask = (freqs >= lo) & (freqs < min(hi, freqs[-1]))
    if not np.any(mask):
        return -120.0
    return _db(np.sqrt(np.mean(spec[mask])))


def _safe_corr(left: np.ndarray, right: np.ndarray) -> float:
    if len(left) < 2 or np.std(left) < 1e-9 or np.std(right) < 1e-9:
        return 1.0
    return float(np.clip(np.corrcoef(left, right)[0, 1], -1.0, 1.0))


def _segment_spectral(mono: np.ndarray, sr: int, segment_sec: float) -> list[dict[str, Any]]:
    hop = max(256, int(segment_sec * sr))
    results: list[dict[str, Any]] = []
    bands = {
        "sub": (20, 60), "bass": (60, 150), "low_mid": (150, 500),
        "mid": (500, 2000), "presence": (2000, 6000), "high": (6000, 12000),
        "air": (12000, 20000),
    }
    for start in range(0, len(mono), hop):
        end = min(len(mono), start + hop)
        chunk = mono[start:end]
        if len(chunk) < max(int(sr), 1024):
            continue
        n_fft = min(8192, 2 ** int(np.floor(np.log2(len(chunk)))))
        n_fft = max(1024, n_fft)
        spec = np.abs(librosa.stft(chunk, n_fft=n_fft, hop_length=max(256, n_fft // 4), window="hann"))
        power = spec ** 2
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
        total = float(np.sum(power[(freqs >= 20) & (freqs <= min(20000, sr / 2))]) + 1e-12)
        energy = {}
        for name, (lo, hi) in bands.items():
            mask = (freqs >= lo) & (freqs < min(hi, sr / 2))
            energy[name] = float(np.sum(power[mask]) / total * 100.0) if np.any(mask) else 0.0
        centroid = float(np.median(librosa.feature.spectral_centroid(S=spec, sr=sr)))
        rolloff = float(np.median(librosa.feature.spectral_rolloff(S=spec, sr=sr, roll_percent=0.85)))
        flatness = float(np.median(librosa.feature.spectral_flatness(S=spec)))
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        peak = float(np.max(np.abs(chunk)))
        results.append({
            "start": round(start / sr, 2), "end": round(end / sr, 2),
            "rms_db": round(_db(rms), 2), "peak_db": round(_db(peak), 2),
            "crest_db": round(_db(peak / max(rms, 1e-9)), 2),
            "centroid_hz": round(centroid, 1), "rolloff_hz": round(rolloff, 1),
            "flatness": round(flatness, 4), "bands": {k: round(v, 3) for k, v in energy.items()},
        })
    return results


def _stereo_map(y: np.ndarray, sr: int, segment_sec: float) -> list[dict[str, Any]]:
    if y.shape[0] < 2:
        return []
    left, right = y[0], y[1]
    hop = max(1, int(segment_sec * sr))
    results = []
    for start in range(0, len(left), hop):
        end = min(len(left), start + hop)
        if end - start < sr:
            continue
        l, r = left[start:end], right[start:end]
        mid = (l + r) * 0.5
        side = (l - r) * 0.5
        mid_rms = np.sqrt(np.mean(mid ** 2))
        side_rms = np.sqrt(np.mean(side ** 2))
        width_db = _db(side_rms / max(mid_rms, 1e-9))
        side_pct = float(np.clip((side_rms / max(mid_rms + side_rms, 1e-9)) * 100.0, 0, 100))
        corr = _safe_corr(l, r)
        balance = _db(np.sqrt(np.mean(l ** 2)) / max(np.sqrt(np.mean(r ** 2)), 1e-9))
        results.append({
            "start": round(start / sr, 2), "end": round(end / sr, 2),
            "correlation": round(corr, 3), "width_db": round(width_db, 2),
            "side_percent": round(side_pct, 1), "lr_balance_db": round(balance, 2),
        })
    return results


def _transient_map(mono: np.ndarray, sr: int, duration: float, segment_sec: float) -> dict[str, Any]:
    onset = librosa.onset.onset_strength(y=mono, sr=sr, hop_length=512, aggregate=np.median)
    frames = librosa.onset.onset_detect(onset_envelope=onset, sr=sr, hop_length=512, backtrack=False, units="time")
    if len(frames):
        strength = np.asarray(onset)
        onset_frames = librosa.time_to_frames(frames, sr=sr, hop_length=512)
        vals = strength[np.clip(onset_frames, 0, len(strength) - 1)]
        threshold = float(np.percentile(strength, 75)) if len(strength) else 0.0
        strong_times = frames[vals >= threshold]
    else:
        strong_times = np.array([])
    bins = []
    step = max(1.0, float(segment_sec))
    for start in np.arange(0.0, duration, step):
        end = min(duration, start + step)
        count = int(np.sum((frames >= start) & (frames < end)))
        strong = int(np.sum((strong_times >= start) & (strong_times < end)))
        bins.append({"start": round(float(start), 2), "end": round(float(end), 2), "count": count, "strong": strong})
    density = (len(frames) / max(duration, 1e-9))
    return {
        "onsets": [round(float(x), 3) for x in frames[:400]],
        "strong_onsets": [round(float(x), 3) for x in strong_times[:160]],
        "events": bins,
        "onsets_per_sec": round(float(density), 3),
        "peak_density": max((x["count"] for x in bins), default=0),
    }


def _vocal_events(mono: np.ndarray, sr: int, segment_sec: float) -> dict[str, Any]:
    # Downsample for the expensive pitch estimator while keeping enough detail for musical events.
    target_sr = 22050 if sr > 22050 else sr
    y = librosa.resample(mono, orig_sr=sr, target_sr=target_sr) if sr != target_sr else mono
    hop = 512
    try:
        f0, voiced, prob = librosa.pyin(y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C6"), sr=target_sr, frame_length=2048, hop_length=hop)
    except Exception:
        return {"status": "unavailable", "events": []}
    times = librosa.frames_to_time(np.arange(len(f0)), sr=target_sr, hop_length=hop)
    valid = np.isfinite(f0) & (prob > 0.55)
    events = []
    step = max(1.0, float(segment_sec))
    duration = len(y) / target_sr
    for start in np.arange(0.0, duration, step):
        end = min(duration, start + step)
        mask = valid & (times >= start) & (times < end)
        if not np.any(mask):
            events.append({"start": round(float(start), 2), "end": round(float(end), 2), "voiced_percent": 0.0, "median_midi": None, "pitch_drift": None})
            continue
        midi = librosa.hz_to_midi(f0[mask])
        drift = float(np.std(np.diff(midi))) if len(midi) > 1 else 0.0
        events.append({
            "start": round(float(start), 2), "end": round(float(end), 2),
            "voiced_percent": round(float(np.mean(mask) * 100.0), 1),
            "median_midi": round(float(np.median(midi)), 2),
            "pitch_drift": round(drift, 3),
        })
    active = [e for e in events if e["median_midi"] is not None]
    return {
        "status": "detected" if active else "no_confident_pitch",
        "events": active,
        "voiced_ratio": round(float(np.mean(valid) * 100.0), 1),
    }


def _findings(spectral: list[dict[str, Any]], stereo: list[dict[str, Any]], transients: dict[str, Any], vocal: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if spectral:
        med = {k: float(np.median([x["bands"][k] for x in spectral])) for k in spectral[0]["bands"]}
        rules = [
            ("sub", med["sub"] > 12, "Excess sub energy", "20–60 Hz", "dynamic_sub_control", "Low-end headroom may be consumed by sub content."),
            ("bass", med["bass"] > 30, "Bass concentration", "60–150 Hz", "dynamic_bass_control", "Bass is carrying more energy than the track profile usually needs."),
            ("low_mid", med["low_mid"] > 22, "Low-mid buildup", "150–500 Hz", "dynamic_low_mid_control", "This region can reduce separation and vocal clarity."),
            ("presence", med["presence"] > 28, "Presence pressure", "2–6 kHz", "dynamic_presence_control", "The vocal and upper-mid region may become fatiguing at high density."),
            ("air", med["air"] < 3, "Low air", "12–20 kHz", "air_shelf", "The top octave is comparatively quiet; only a restrained lift is justified."),
        ]
        for key, hit, title, band, action, reason in rules:
            if hit:
                findings.append({"type": key, "title": title, "band": band, "action": action, "severity": "medium", "reason": reason})
    if stereo:
        corr = np.asarray([x["correlation"] for x in stereo])
        width = np.asarray([x["width_db"] for x in stereo])
        if np.min(corr) < 0.0:
            findings.append({"type": "phase", "title": "Phase risk", "band": "stereo field", "action": "stereo_check", "severity": "high", "reason": "A segment crosses into negative L/R correlation."})
        elif np.min(corr) < 0.25:
            findings.append({"type": "phase", "title": "Weak mono compatibility", "band": "stereo field", "action": "stereo_check", "severity": "medium", "reason": "Some segments have low L/R correlation."})
        if np.max(width) > 3.0:
            findings.append({"type": "width", "title": "Very wide section", "band": "stereo field", "action": "stereo_check", "severity": "low", "reason": "Side energy becomes dominant in at least one section."})
    if transients.get("peak_density", 0) >= 10:
        findings.append({"type": "transient", "title": "High transient density", "band": "rhythmic events", "action": "transient_guard", "severity": "low", "reason": "Dense onset activity can make limiting feel more aggressive."})
    if vocal.get("status") == "detected":
        drifts = [float(x["pitch_drift"]) for x in vocal.get("events", []) if x.get("pitch_drift") is not None and x.get("voiced_percent", 0) > 20]
        if drifts and float(np.median(drifts)) > 0.22:
            findings.append({"type": "vocal", "title": "Vocal pitch movement", "band": "vocal", "action": "vocal_review", "severity": "low", "reason": "The full-mix pitch contour shows noticeable movement; this is an observation, not a correction command."})
    return findings


def analyze_audio(path: str | Path, segment_sec: float = 5.0) -> dict[str, Any]:
    path = Path(path)
    y, sr = _load(path)
    mono = np.mean(y, axis=0)
    duration = len(mono) / sr if sr else 0.0
    spectral = _segment_spectral(mono, sr, segment_sec)
    stereo = _stereo_map(y, sr, segment_sec)
    transients = _transient_map(mono, sr, duration, segment_sec)
    vocal = _vocal_events(mono, sr, max(segment_sec, 5.0))
    findings = _findings(spectral, stereo, transients, vocal)
    return {
        "version": "6.2",
        "segment_sec": segment_sec,
        "duration_sec": round(float(duration), 3),
        "spectral": {"segments": spectral, "count": len(spectral)},
        "stereo": {"segments": stereo, "count": len(stereo)},
        "transients": transients,
        "vocal_events": vocal,
        "findings": findings,
        "summary": {
            "finding_count": len(findings),
            "high": sum(1 for x in findings if x["severity"] == "high"),
            "medium": sum(1 for x in findings if x["severity"] == "medium"),
            "low": sum(1 for x in findings if x["severity"] == "low"),
        },
    }
