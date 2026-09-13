from pathlib import Path
import json

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

import mastering


# ============================================================
# PROCESSING EXECUTOR 1.0
# Applies adaptive processing_plan to any song.
# ============================================================


def _ensure_stereo(audio):
    audio = np.asarray(audio, dtype=np.float64)

    if audio.ndim == 1:
        audio = audio[:, None]

    if audio.ndim > 2:
        audio = audio.reshape(audio.shape[0], -1)

    if audio.shape[1] > 2:
        audio = audio[:, :2]

    return np.nan_to_num(
        audio,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )


def _band_filter(audio, sr, low=None, high=None):
    nyquist = sr / 2.0

    if low is not None:
        low = max(10.0, float(low))

    if high is not None:
        high = min(float(high), nyquist * 0.95)

    if low is not None and high is not None:
        if low >= high:
            return audio

        sos = butter(
            4,
            [low / nyquist, high / nyquist],
            btype="bandpass",
            output="sos",
        )

    elif low is not None:
        sos = butter(
            4,
            low / nyquist,
            btype="highpass",
            output="sos",
        )

    elif high is not None:
        sos = butter(
            4,
            high / nyquist,
            btype="lowpass",
            output="sos",
        )

    else:
        return audio

    return sosfiltfilt(sos, audio, axis=0)


def _apply_band_gain(audio, sr, low, high, gain_db):
    """
    Gentle static correction for a detected problem.

    The gain is intentionally capped so the executor cannot
    destroy the source because of an incorrect analysis.
    """

    gain_db = float(np.clip(gain_db, -3.0, 3.0))

    if abs(gain_db) < 0.05:
        return audio

    band = _band_filter(
        audio,
        sr,
        low=low,
        high=high,
    )

    linear = 10.0 ** (gain_db / 20.0)

    return audio + band * (linear - 1.0)


def _apply_dynamic_band_control(
    audio,
    sr,
    low,
    high,
    gain_db,
):
    """
    Conservative dynamic-style band control.

    Instead of applying the full correction permanently,
    the detector increases the correction only when the
    selected band becomes relatively strong.
    """

    requested = float(gain_db)

    # Safety limits.
    requested = float(
        np.clip(
            requested,
            -3.0,
            0.0,
        )
    )

    if requested >= -0.05:
        return audio

    band = _band_filter(
        audio,
        sr,
        low=low,
        high=high,
    )

    # Envelope.
    envelope = np.mean(
        np.abs(band),
        axis=1,
    )

    if len(envelope) == 0:
        return audio

    reference = np.percentile(
        envelope,
        65,
    )

    if reference <= 1e-9:
        return audio

    ratio = envelope / reference

    # Only start acting above the reference.
    amount = np.clip(
        (ratio - 1.0) / 1.5,
        0.0,
        1.0,
    )

    # Smooth the control signal.
    window = max(
        1,
        int(sr * 0.05),
    )

    kernel = np.ones(window) / window

    if len(amount) > window:
        amount = np.convolve(
            amount,
            kernel,
            mode="same",
        )

    gain_linear = 10.0 ** (
        (requested * amount) / 20.0
    )

    return audio + band * (
        gain_linear[:, None] - 1.0
    )


def _apply_action(
    audio,
    sr,
    action,
    gain_db,
):
    """
    Maps planner actions to conservative processing.
    """

    if action == "dynamic_presence_control":
        return _apply_dynamic_band_control(
            audio,
            sr,
            2000,
            6000,
            gain_db,
        )

    if action == "dynamic_low_mid_control":
        return _apply_dynamic_band_control(
            audio,
            sr,
            150,
            500,
            gain_db,
        )

    if action == "dynamic_sub_control":
        return _apply_dynamic_band_control(
            audio,
            sr,
            20,
            60,
            gain_db,
        )

    if action == "air_shelf":
        gain_db = float(
            np.clip(
                gain_db,
                0.0,
                2.0,
            )
        )

        return mastering.apply_shelf(
            audio,
            sr,
            cutoff=12000,
            gain_db=gain_db,
            high=True,
        )

    return audio


def _safe_write(
    path,
    audio,
    sr,
):
    audio = np.asarray(
        audio,
        dtype=np.float64,
    )

    peak = np.max(
        np.abs(audio)
    )

    if peak > 0.999:
        audio = audio / peak * 0.999

    sf.write(
        path,
        audio.astype(np.float32),
        sr,
        subtype="PCM_24",
    )


def execute_processing_plan(
    input_path,
    output_path,
    processing_plan,
):
    """
    Apply processing_plan to input_path.

    Returns a structured report containing:
    - input/output
    - original analysis
    - final analysis
    - applied steps
    """

    input_path = Path(input_path)
    output_path = Path(output_path)

    audio, sr = sf.read(
        str(input_path),
        always_2d=True,
    )

    audio = _ensure_stereo(audio)

    original_audio = audio.copy()

    original_analysis = mastering.analyze_master(
        audio,
        sr,
    )

    steps = processing_plan.get(
        "steps",
        [],
    )

    applied_steps = []

    processed = audio.copy()

    for step in steps:
        action = step.get(
            "action",
            "",
        )

        gain_db = float(
            step.get(
                "gain_db",
                0.0,
            )
        )

        problem = step.get(
            "problem",
            "",
        )

        priority = step.get(
            "priority",
            "",
        )

        before_peak = float(
            np.max(
                np.abs(processed)
            )
        )

        processed = _apply_action(
            processed,
            sr,
            action,
            gain_db,
        )

        processed = np.nan_to_num(
            processed,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        after_peak = float(
            np.max(
                np.abs(processed)
            )
        )

        applied_steps.append(
            {
                "problem": problem,
                "action": action,
                "gain_db": gain_db,
                "priority": priority,
                "peak_before": before_peak,
                "peak_after": after_peak,
            }
        )

    _safe_write(
        output_path,
        processed,
        sr,
    )

    final_audio, final_sr = sf.read(
        str(output_path),
        always_2d=True,
    )

    final_audio = _ensure_stereo(
        final_audio
    )

    final_analysis = mastering.analyze_master(
        final_audio,
        final_sr,
    )

    report = {
        "engine": "Processing Executor 1.0",
        "input": str(input_path),
        "output": str(output_path),
        "sample_rate": sr,
        "steps_count": len(applied_steps),
        "applied_steps": applied_steps,
        "original": original_analysis,
        "final": final_analysis,
    }

    return report


def save_report(
    report,
    path,
):
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2,
        )


if __name__ == "__main__":
    print(
        "PROCESSING EXECUTOR 1.0"
    )