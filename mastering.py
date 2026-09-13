from pathlib import Path
import json
import numpy as np
import soundfile as sf
import pyloudnorm as pyln

from scipy.signal import butter, sosfilt, resample_poly


# ============================================================
# ELIZA BETT MUSIC LAB
# AUTO MASTERING ENGINE v0.5
# ============================================================


def db_to_linear(db):
    return 10.0 ** (db / 20.0)


def linear_to_db(value):
    return 20.0 * np.log10(max(float(value), 1e-12))


def peak_dbfs(audio):
    return linear_to_db(np.max(np.abs(audio)))


def rms_dbfs(audio):
    rms = np.sqrt(np.mean(audio ** 2))
    return linear_to_db(rms)


def loudness(audio, sr):
    meter = pyln.Meter(sr)

    if audio.ndim == 1:
        return float(
            meter.integrated_loudness(audio)
        )

    return float(
        meter.integrated_loudness(audio)
    )


def true_peak_dbfs(audio, sr):
    """Estimate true peak using 4x oversampling along the time axis."""
    if audio.ndim == 1:
        audio = audio[:, None]

    audio = np.asarray(audio, dtype=np.float64)

    oversampled = resample_poly(
        audio,
        4,
        1,
        axis=0
    )

    peak = np.max(np.abs(oversampled))
    return float(linear_to_db(max(peak, 1e-12)))

def highpass(audio, sr, cutoff):
    sos = butter(
        4,
        cutoff,
        btype="highpass",
        fs=sr,
        output="sos"
    )

    return sosfilt(
        sos,
        audio,
        axis=0
    )


def lowpass(audio, sr, cutoff):
    sos = butter(
        4,
        cutoff,
        btype="lowpass",
        fs=sr,
        output="sos"
    )

    return sosfilt(
        sos,
        audio,
        axis=0
    )


def bandpass(audio, sr, low, high):
    sos = butter(
        4,
        [low, high],
        btype="bandpass",
        fs=sr,
        output="sos"
    )

    return sosfilt(
        sos,
        audio,
        axis=0
    )


def band_rms(audio, sr, low, high):
    band = bandpass(
        audio,
        sr,
        low,
        high
    )

    return float(
        np.sqrt(
            np.mean(band ** 2)
        )
    )


def compressor(audio, threshold_db=-18.0,
                ratio=1.5,
                attack_ms=30.0,
                release_ms=120.0):
    """
    Simple broadband compressor.
    """

    if audio.ndim == 1:
        audio = audio[:, None]

    detector = np.max(
        np.abs(audio),
        axis=1
    )

    detector_db = 20.0 * np.log10(
        np.maximum(detector, 1e-8)
    )

    gain_db = np.zeros_like(
        detector_db
    )

    over = detector_db > threshold_db

    gain_db[over] = (
        threshold_db
        + (
            detector_db[over]
            - threshold_db
        ) / ratio
        - detector_db[over]
    )

    sr_estimate = 48000.0

    attack_coeff = np.exp(
        -1.0 /
        (
            sr_estimate
            * attack_ms
            / 1000.0
        )
    )

    release_coeff = np.exp(
        -1.0 /
        (
            sr_estimate
            * release_ms
            / 1000.0
        )
    )

    smoothed = np.zeros_like(
        gain_db
    )

    previous = 0.0

    for i, target in enumerate(
        gain_db
    ):

        if target < previous:
            coeff = attack_coeff
        else:
            coeff = release_coeff

        previous = (
            coeff * previous
            + (1.0 - coeff) * target
        )

        smoothed[i] = previous

    gain = db_to_linear(
        smoothed
    )

    return audio * gain[:, None]


def apply_shelf(audio, sr,
                cutoff,
                gain_db,
                high=True):
    """
    Gentle first-order shelving-style tilt.
    """

    if abs(gain_db) < 0.05:
        return audio

    if audio.ndim == 1:
        audio = audio[:, None]

    if high:
        filtered = lowpass(
            audio,
            sr,
            cutoff
        )

        high_part = (
            audio - filtered
        )

        return (
            filtered
            + high_part
            * db_to_linear(gain_db)
        )

    filtered = highpass(
        audio,
        sr,
        cutoff
    )

    low_part = (
        audio - filtered
    )

    return (
        low_part
        * db_to_linear(gain_db)
        + filtered
    )


def apply_mid_cut(audio, sr,
                  low,
                  high,
                  gain_db):
    """
    Broad musical EQ band.
    """

    if abs(gain_db) < 0.05:
        return audio

    if audio.ndim == 1:
        audio = audio[:, None]

    band = bandpass(
        audio,
        sr,
        low,
        high
    )

    gain = db_to_linear(
        gain_db
    )

    return (
        audio
        + band * (gain - 1.0)
    )


def limiter(audio, ceiling_db=-1.0, release_ms=80.0):
    """True-peak aware broadband limiter using 4x oversampling."""
    if audio.ndim == 1:
        audio = audio[:, None]

    audio = np.asarray(audio, dtype=np.float64)
    ceiling = db_to_linear(ceiling_db)

    # Oversample only for detection. Processing remains at the original rate.
    oversampled = resample_poly(audio, 4, 1, axis=0)

    # Map each original sample to the maximum nearby oversampled peak.
    detector = np.zeros(audio.shape[0], dtype=np.float64)
    ratio = oversampled.shape[0] / audio.shape[0]

    for i in range(audio.shape[0]):
        start = int(i * ratio)
        end = min(int((i + 1) * ratio) + 4, oversampled.shape[0])
        if start < end:
            detector[i] = np.max(np.abs(oversampled[start:end]))

    gain = np.ones_like(detector)
    release_coeff = np.exp(-1.0 / (48000.0 * release_ms / 1000.0))
    previous_gain = 1.0

    for i, peak in enumerate(detector):
        if peak > ceiling:
            target_gain = ceiling / max(peak, 1e-12)
        else:
            target_gain = 1.0

        if target_gain < previous_gain:
            previous_gain = target_gain
        else:
            previous_gain = (
                release_coeff * previous_gain
                + (1.0 - release_coeff) * target_gain
            )

        gain[i] = previous_gain

    return audio * gain[:, None]

def soft_clip(audio,
              drive=1.0):
    """
    Gentle saturation / peak control.
    """

    return np.tanh(
        audio * drive
    ) / np.tanh(drive)


def analyze_master(
    audio,
    sr
):
    """
    Analyze the complete stereo mix.
    """

    if audio.ndim == 1:
        audio = audio[:, None]

    result = {}

    result["sample_rate"] = int(sr)
    result["channels"] = int(
        audio.shape[1]
    )

    result["duration_sec"] = round(
        len(audio) / sr,
        3
    )

    result["lufs"] = round(
        loudness(audio, sr),
        2
    )

    result["rms_dbfs"] = round(
        rms_dbfs(audio),
        2
    )

    result["peak_dbfs"] = round(
        peak_dbfs(audio),
        2
    )

    result["true_peak_dbfs"] = round(
        true_peak_dbfs(audio, sr),
        2
    )

    # Frequency regions

    result["sub_rms"] = band_rms(
        audio,
        sr,
        20,
        60
    )

    result["bass_rms"] = band_rms(
        audio,
        sr,
        60,
        150
    )

    result["low_mid_rms"] = band_rms(
        audio,
        sr,
        150,
        400
    )

    result["mid_rms"] = band_rms(
        audio,
        sr,
        400,
        2000
    )

    result["presence_rms"] = band_rms(
        audio,
        sr,
        2000,
        6000
    )

    result["air_rms"] = band_rms(
        audio,
        sr,
        6000,
        min(18000, sr // 2 - 100)
    )

    # Stereo

    if audio.shape[1] >= 2:

        left = audio[:, 0]
        right = audio[:, 1]

        mid = (
            left + right
        ) / 2.0

        side = (
            left - right
        ) / 2.0

        mid_rms = np.sqrt(
            np.mean(mid ** 2)
        )

        side_rms = np.sqrt(
            np.mean(side ** 2)
        )

        result["stereo_width_db"] = round(
            linear_to_db(
                side_rms
                / max(mid_rms, 1e-12)
            ),
            2
        )

        result["mono_correlation"] = round(
            float(
                np.corrcoef(
                    left,
                    right
                )[0, 1]
            ),
            3
        )

    else:

        result["stereo_width_db"] = 0.0
        result["mono_correlation"] = 1.0

    return result


def adaptive_analyze(audio, sr):
    """Adaptive mastering analysis: spectrum, dynamics and stereo."""
    audio = np.asarray(audio, dtype=np.float64)

    if audio.ndim == 1:
        audio = audio[:, None]
    if audio.shape[1] > 2:
        audio = audio[:, :2]

    # ---------- BASIC ----------
    duration = float(len(audio) / sr)
    lufs = loudness(audio, sr)
    rms = rms_dbfs(audio)
    peak = peak_dbfs(audio)
    true_peak = true_peak_dbfs(audio, sr)
    crest = float(peak - rms)

    # ---------- STEREO ----------
    if audio.shape[1] >= 2:
        left = audio[:, 0]
        right = audio[:, 1]

        mid = (left + right) * 0.5
        side = (left - right) * 0.5

        mid_rms = np.sqrt(np.mean(mid ** 2) + 1e-12)
        side_rms = np.sqrt(np.mean(side ** 2) + 1e-12)

        stereo_width_db = float(20.0 * np.log10(max(side_rms, 1e-12) / max(mid_rms, 1e-12)))

        correlation = float(
            np.corrcoef(left, right)[0, 1]
        ) if np.std(left) > 1e-10 and np.std(right) > 1e-10 else 1.0

        balance_db = float(
            20.0 * np.log10(
                max(np.sqrt(np.mean(left ** 2)), 1e-12)
                / max(np.sqrt(np.mean(right ** 2)), 1e-12)
            )
        )
    else:
        stereo_width_db = -120.0
        correlation = 1.0
        balance_db = 0.0

    # ---------- SPECTRUM ----------
    mono = np.mean(audio, axis=1)
    n_fft = min(65536, max(4096, 2 ** int(np.ceil(np.log2(min(len(mono), 65536))))))
    window = np.hanning(len(mono))
    if len(mono) > n_fft:
        step = n_fft // 2
        chunks = []
        for start in range(0, len(mono) - n_fft + 1, step):
            chunk = mono[start:start+n_fft] * np.hanning(n_fft)
            chunks.append(np.abs(np.fft.rfft(chunk)))
        spectrum = np.mean(chunks, axis=0)
        freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    else:
        padded = np.zeros(n_fft)
        padded[:len(mono)] = mono
        spectrum = np.abs(np.fft.rfft(padded * np.hanning(n_fft)))
        freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

    spectrum_power = spectrum ** 2

    bands = {
        'sub_20_60': (20, 60),
        'bass_60_150': (60, 150),
        'low_mid_150_500': (150, 500),
        'mid_500_2000': (500, 2000),
        'presence_2000_6000': (2000, 6000),
        'high_6000_12000': (6000, 12000),
        'air_12000_20000': (12000, 20000),
    }

    band_energy = {}
    total_energy = float(np.sum(spectrum_power[(freqs >= 20) & (freqs <= min(20000, sr / 2))]) + 1e-12)

    for name, (low, high) in bands.items():
        mask = (freqs >= low) & (freqs < min(high, sr / 2))
        energy = float(np.sum(spectrum_power[mask]))
        band_energy[name] = round(100.0 * energy / total_energy, 3)

    # ---------- DIAGNOSTIC FLAGS ----------
    flags = []
    recommendations = []

    if band_energy['sub_20_60'] > 10:
        flags.append('excess_sub')
        recommendations.append('Контролировать sub 20-60 Hz')

    if band_energy['bass_60_150'] > 25:
        flags.append('excess_bass')
        recommendations.append('Проверить избыток bass 60-150 Hz')

    if band_energy['low_mid_150_500'] > 18:
        flags.append('mud_low_mid')
        recommendations.append('Проверить муть 150-500 Hz')

    if band_energy['presence_2000_6000'] > 30:
        flags.append('harsh_presence')
        recommendations.append('Проверить резкость 2-6 kHz')

    if band_energy['air_12000_20000'] < 5:
        flags.append('low_air')
        recommendations.append('Проверить недостаток air 12-20 kHz')

    if crest < 6:
        flags.append('low_crest')
        recommendations.append('Микс уже сильно сжат - осторожно с компрессией')
    elif crest > 14:
        flags.append('high_crest')
        recommendations.append('Большой crest factor - возможна дополнительная динамическая обработка')

    if correlation < 0.3:
        flags.append('stereo_phase_risk')
        recommendations.append('Проверить фазу и mono compatibility')
    elif correlation > 0.95 and stereo_width_db < -15:
        flags.append('narrow_stereo')
        recommendations.append('Стерео очень узкое')

    analysis = {
        'duration_sec': round(duration, 3),
        'lufs': round(float(lufs), 3),
        'rms_dbfs': round(float(rms), 3),
        'peak_dbfs': round(float(peak), 3),
        'true_peak_dbfs': round(float(true_peak), 3),
        'crest_factor_db': round(crest, 3),
        'stereo_width_db': round(stereo_width_db, 3),
        'mono_correlation': round(correlation, 4),
        'lr_balance_db': round(balance_db, 3),
        'band_energy_percent': band_energy,
        'flags': flags,
        'recommendations': recommendations,
    }

    return analysis


def auto_master(input_path, output_path, target_lufs=-10.5, ceiling_db=-1.0, intensity='balanced'):
    audio, sr = sf.read(input_path, always_2d=True)
    audio = np.asarray(audio, dtype=np.float64)

    if audio.ndim == 1:
        audio = audio[:, None]
    elif audio.ndim > 2:
        audio = audio.reshape(audio.shape[0], -1)

    if audio.shape[1] > 2:
        audio = audio[:, :2]

    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)

    original = analyze_master(audio, sr)

    # Corrective high-pass
    audio = highpass(audio, sr, 25)

    # Musical compression
    if intensity == 'gentle':
        comp_amount = 0.10
    elif intensity == 'aggressive':
        comp_amount = 0.28
    else:
        comp_amount = 0.18

    audio = compressor(
        audio,
        threshold_db=-18.0,
        ratio=1.0 + comp_amount * 2.5,
        attack_ms=25.0,
        release_ms=120.0
    )

    # Tonal shaping
    audio = apply_shelf(
        audio,
        sr,
        9000,
        0.8 if intensity != 'aggressive' else 1.2,
        'high'
    )

    audio = apply_mid_cut(
        audio,
        sr,
        200,
        400,
        -0.6 if intensity != 'aggressive' else -1.0
    )

    # Saturation
    drive = 1.015 if intensity == 'gentle' else (1.035 if intensity == 'balanced' else 1.055)
    audio = soft_clip(audio, drive=drive)

    # Loudness target before limiting
    current_lufs = loudness(audio, sr)
    gain_db = float(target_lufs - current_lufs)
    gain_db = float(np.clip(gain_db, -6.0, 12.0))
    audio *= db_to_linear(gain_db)

    # Peak limiting. This reduces peaks instead of turning down the entire mix.
    for _ in range(5):
        audio = limiter(audio, ceiling_db=ceiling_db, release_ms=80.0)
        current_lufs = loudness(audio, sr)
        delta_db = float(target_lufs - current_lufs)

        if abs(delta_db) < 0.05:
            break

        # Gain is allowed because limiter will catch the new peaks.
        step_db = float(np.clip(delta_db, -1.0, 1.5))
        audio *= db_to_linear(step_db)

    # Final limiter pass
    audio = limiter(audio, ceiling_db=ceiling_db, release_ms=80.0)

    # Final LUFS trim with another limiter pass
    final_lufs = loudness(audio, sr)
    final_delta = float(target_lufs - final_lufs)

    if abs(final_delta) > 0.02:
        audio *= db_to_linear(final_delta)
        audio = limiter(audio, ceiling_db=ceiling_db, release_ms=80.0)

    audio = np.clip(audio, -1.0, 1.0)
    sf.write(output_path, audio.astype(np.float32), sr, subtype='PCM_24')

    final = analyze_master(audio, sr)

    report = {
        'input': str(input_path),
        'output': str(output_path),
        'target_lufs': float(target_lufs),
        'ceiling_db': float(ceiling_db),
        'intensity': intensity,
        'original': original,
        'final': final,
        'lufs_error_db': round(float(final['lufs'] - target_lufs), 3),
    }

    return report

def save_report(
    report,
    path
):

    path = Path(path)

    path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )
