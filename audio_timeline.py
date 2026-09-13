from __future__ import annotations

from pathlib import Path
from typing import Any

import librosa
import numpy as np
import pyloudnorm as pyln
import soundfile as sf


def _db(x: float, floor: float = 1e-9) -> float:
    return float(20.0 * np.log10(max(float(x), floor)))


def _load(path: Path):
    y, sr = librosa.load(path, sr=None, mono=False)
    y = np.asarray(y, dtype=np.float32)
    if y.ndim == 1:
        y = y[None, :]
    return y, int(sr)


def build_timeline(path: Path, points: int = 1200, segment_sec: float = 3.0) -> dict[str, Any]:
    y, sr = _load(path)
    mono = np.mean(y, axis=0)
    duration = mono.size / sr if mono.size else 0.0
    # Envelope for a clean, low-cost waveform overview.
    n = min(max(int(points), 240), 1800)
    edges = np.linspace(0, mono.size, n + 1, dtype=np.int64)
    peak = np.zeros(n, dtype=np.float32)
    rms = np.zeros(n, dtype=np.float32)
    for i in range(n):
        chunk = mono[edges[i]:edges[i + 1]]
        if chunk.size:
            peak[i] = np.max(np.abs(chunk))
            rms[i] = np.sqrt(np.mean(chunk * chunk))
    peak_db = np.clip(20 * np.log10(np.maximum(peak, 1e-8)), -60, 0)
    rms_db = np.clip(20 * np.log10(np.maximum(rms, 1e-8)), -60, 0)

    # Segment loudness follows the BS.1770 family conceptually: loudness is
    # a K-weighted/gated programme measure. pyloudnorm provides the local
    # implementation; these are segment descriptors, not a compliance meter.
    meter = pyln.Meter(sr)
    step = max(0.5, float(segment_sec))
    starts = np.arange(0.0, duration, step)
    segments = []
    for start in starts:
        end = min(duration, start + step)
        if end - start < 0.4:
            continue
        s0, s1 = int(start * sr), int(end * sr)
        chunk = mono[s0:s1]
        if chunk.size < int(0.4 * sr):
            continue
        try:
            loud = float(meter.integrated_loudness(chunk))
        except Exception:
            loud = float(_db(np.sqrt(np.mean(chunk * chunk))))
        crest = _db(np.max(np.abs(chunk)) / max(np.sqrt(np.mean(chunk * chunk)), 1e-8))
        segments.append({
            "t": round(float((start + end) / 2), 3),
            "start": round(float(start), 3),
            "end": round(float(end), 3),
            "lufs": round(loud, 2),
            "rms_dbfs": round(_db(np.sqrt(np.mean(chunk * chunk))), 2),
            "crest_db": round(crest, 2),
        })

    return {
        "duration_sec": round(float(duration), 3),
        "sample_rate": sr,
        "waveform": {
            "peak_db": [round(float(v), 2) for v in peak_db],
            "rms_db": [round(float(v), 2) for v in rms_db],
        },
        "loudness": {
            "window_sec": step,
            "segments": segments,
            "note": "Segment loudness visualization; use the main meter for final integrated compliance measurements.",
        },
    }
