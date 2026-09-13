from __future__ import annotations
from pathlib import Path
from typing import Any
import numpy as np
import librosa

VERSION = "6.9"


def analyze(path: str | Path, bpm: float | None = None) -> dict[str, Any]:
    y, sr = librosa.load(str(path), sr=22050, mono=True)
    y = np.asarray(y, dtype=np.float32)
    duration = len(y) / sr if len(y) else 0.0
    hop = 256
    try:
        f0, voiced_flag, voiced_prob = librosa.pyin(
            y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C6"),
            sr=sr, frame_length=2048, hop_length=hop
        )
    except Exception as exc:
        return {"version": VERSION, "status": "unavailable", "error": str(exc), "phrases": [], "alignment": []}

    times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=hop)
    voiced = np.isfinite(f0) & (np.asarray(voiced_prob) > 0.55)
    # Smooth isolated decisions so phrase detection is useful on a full mix.
    kernel = np.ones(5, dtype=np.int32)
    smoothed = np.convolve(voiced.astype(np.int32), kernel, mode="same") >= 3
    voiced = smoothed

    # A phrase is a contiguous vocal region, allowing short gaps for consonants/breaths.
    gap_frames = max(1, int(round(0.28 * sr / hop)))
    padded = np.r_[False, voiced, False]
    starts = np.flatnonzero(~padded[:-1] & padded[1:])
    ends = np.flatnonzero(padded[:-1] & ~padded[1:])
    raw = []
    for s, e in zip(starts, ends):
        if e <= s:
            continue
        raw.append([float(times[s]), float(times[min(e-1, len(times)-1)] + hop/sr)])
    # Merge nearby vocal regions.
    merged: list[list[float]] = []
    for start, end in raw:
        if merged and start - merged[-1][1] <= 0.28:
            merged[-1][1] = end
        else:
            merged.append([start, end])

    beat_sec = 60.0 / bpm if bpm and bpm > 0 else None
    phrases = []
    for i, (start, end) in enumerate(merged):
        dur = max(0.0, end-start)
        beat_count = dur / beat_sec if beat_sec else None
        # This is a planning budget, not syllable transcription. Approx. 2.2 syllables/sec.
        syllable_budget = int(np.clip(round(dur * 2.2), 1, 28))
        mean_f0 = float(np.nanmedian(f0[(times >= start) & (times < end)])) if np.any(np.isfinite(f0[(times >= start) & (times < end)])) else None
        phrases.append({
            "index": i+1, "start": round(start,3), "end": round(end,3), "duration": round(dur,3),
            "beats_estimate": round(float(beat_count),2) if beat_count is not None else None,
            "syllable_budget_estimate": syllable_budget,
            "mean_pitch_hz": round(mean_f0,1) if mean_f0 else None,
        })

    # Group phrases into lyric lines by a longer gap (or roughly 2–4 phrase units).
    alignment = []
    for i, p in enumerate(phrases):
        gap_after = (phrases[i+1]["start"] - p["end"]) if i+1 < len(phrases) else None
        alignment.append({
            "phrase": p["index"],
            "suggested_line": i+1,
            "gap_after_sec": round(gap_after,3) if gap_after is not None else None,
            "line_end_candidate": bool(gap_after is None or gap_after >= 0.45),
            "writing_note": "fit a concise lyric phrase; preserve room for breath" if p["duration"] < 1.6 else "allow a longer lyric phrase; avoid overpacking",
        })

    voiced_ratio = float(np.mean(voiced)) if len(voiced) else 0.0
    return {
        "version": VERSION,
        "status": "ok",
        "duration_sec": round(duration,3),
        "voiced_ratio": round(voiced_ratio,3),
        "phrase_count": len(phrases),
        "phrases": phrases[:160],
        "alignment": alignment[:160],
        "method_notes": [
            "Full-mix pYIN is used to locate probable pitched vocal phrases; instrumental material can create false positives.",
            "Phrase boundaries are timing candidates, not a word-level vocal transcription.",
            "Syllable budgets are heuristic writing targets derived from phrase duration, not detected syllable counts.",
            "Use detected BPM only when confidence is adequate; beat counts are estimates when BPM is uncertain.",
        ],
    }
