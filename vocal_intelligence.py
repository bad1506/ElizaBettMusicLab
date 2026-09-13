from __future__ import annotations
from pathlib import Path
import numpy as np
import librosa


def analyze_vocal(path: str | Path) -> dict:
    y, sr = librosa.load(str(path), sr=None, mono=True)
    duration = len(y) / sr if sr else 0.0
    f0, voiced_flag, voiced_prob = librosa.pyin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C6'), sr=sr, frame_length=2048, hop_length=256)
    valid = np.isfinite(f0) & (voiced_prob > 0.5)
    if valid.any():
        midi = librosa.hz_to_midi(f0[valid])
        cents = (midi - np.round(midi)) * 100.0
        low = float(np.nanmin(midi)); high = float(np.nanmax(midi)); median = float(np.nanmedian(midi))
        accuracy = float(np.clip(100.0 - np.nanmedian(np.abs(cents)) / 50.0 * 100.0, 0, 100))
        stability = float(np.clip(100.0 - np.nanmedian(np.abs(np.diff(midi))) * 25.0, 0, 100)) if len(midi) > 1 else 100.0
        note_names = [librosa.midi_to_note(round(low)), librosa.midi_to_note(round(median)), librosa.midi_to_note(round(high))]
        pitch_range = high - low
        voiced_ratio = float(valid.mean())
    else:
        low = high = median = pitch_range = 0.0; accuracy = stability = voiced_ratio = 0.0; note_names = ['—','—','—']
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=256)[0]
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    rms_db = float(20*np.log10(max(float(np.sqrt(np.mean(y*y))),1e-12)))
    return {
        'sample_rate': int(sr), 'duration_sec': round(duration,3), 'voiced_ratio': round(voiced_ratio*100,1),
        'lowest_note': note_names[0], 'median_note': note_names[1], 'highest_note': note_names[2],
        'lowest_midi': round(low,2), 'median_midi': round(median,2), 'highest_midi': round(high,2),
        'range_semitones': round(pitch_range,2), 'pitch_accuracy_percent': round(accuracy,1),
        'pitch_stability_percent': round(stability,1), 'rms_dbfs': round(rms_db,2),
        'peak_dbfs': round(20*np.log10(max(peak,1e-12)),2),
        'status': 'detected' if valid.any() else 'no_confident_pitch',
        'method_note': 'Monophonic pitch analysis via librosa.pyin; mix-level estimate, not isolated-vocal transcription.'
    }
