import numpy as np

def spectral_timeline_analyze(audio, sr, segment_sec=10.0):
    if audio.ndim == 1: audio = audio[:, None]
    audio = np.asarray(audio, dtype=np.float64)
    audio = np.nan_to_num(audio)
    if audio.shape[1] > 2: audio = audio[:, :2]
    mono = np.mean(audio[:, :2], axis=1)
    segment_samples = max(int(segment_sec * sr), 1)
    bands = {"sub_20_60": (20,60), "bass_60_150": (60,150), "low_mid_150_500": (150,500), "mid_500_2000": (500,2000), "presence_2000_6000": (2000,6000), "high_6000_12000": (6000,12000), "air_12000_20000": (12000,20000)}
    results = []
    for start in range(0, len(mono), segment_samples):
        end = min(start + segment_samples, len(mono))
        chunk = mono[start:end]
        if len(chunk) < sr: continue
        window = np.hanning(len(chunk))
        spectrum = np.abs(np.fft.rfft(chunk * window)) ** 2
        freqs = np.fft.rfftfreq(len(chunk), 1.0 / sr)
        valid = (freqs >= 20) & (freqs <= min(20000, sr / 2))
        total = np.sum(spectrum[valid]) + 1e-12
        band_energy = {}
        for name, (lo, hi) in bands.items():
            mask = (freqs >= lo) & (freqs < min(hi, sr / 2))
            band_energy[name] = float(np.sum(spectrum[mask]) / total * 100.0)
        rms = np.sqrt(np.mean(chunk ** 2)) + 1e-12
        peak = np.max(np.abs(chunk)) + 1e-12
        rms_db = 20 * np.log10(rms)
        peak_db = 20 * np.log10(peak)
        crest_db = peak_db - rms_db
        problems = []
        if band_energy["sub_20_60"] > 12: problems.append("excess_sub")
        if band_energy["bass_60_150"] > 30: problems.append("excess_bass")
        if band_energy["low_mid_150_500"] > 22: problems.append("mud_low_mid")
        if band_energy["presence_2000_6000"] > 28: problems.append("harsh_presence")
        if band_energy["air_12000_20000"] < 3: problems.append("low_air")
        if crest_db < 5: problems.append("overcompressed")
        results.append({"time_start": round(start/sr,2), "time_end": round(end/sr,2), "rms_db": round(float(rms_db),3), "peak_db": round(float(peak_db),3), "crest_db": round(float(crest_db),3), "bands": {k: round(v,3) for k,v in band_energy.items()}, "problems": problems})
    if not results: return {"segment_sec": segment_sec, "segments": [], "problem_segments": [], "track_profile": {}}
    keys = list(bands.keys())
    profile = {k: float(np.median([x["bands"][k] for x in results])) for k in keys}
    for item in results:
        relative = {}
        problems = []
        for k in keys:
            value = item["bands"][k]
            base = profile[k] + 1e-9
            relative[k] = round(float(value / base), 3)
        if relative["sub_20_60"] > 1.50: problems.append("relative_excess_sub")
        if relative["bass_60_150"] > 1.50: problems.append("relative_excess_bass")
        if relative["low_mid_150_500"] > 1.45: problems.append("relative_mud")
        if relative["presence_2000_6000"] > 1.45: problems.append("relative_harshness")
        if relative["air_12000_20000"] < 0.60: problems.append("relative_low_air")
        item["relative"] = relative
        item["problems"] = problems
    return {"segment_sec": segment_sec, "segments": results, "problem_segments": [x for x in results if x["problems"]], "track_profile": {k: round(v, 3) for k, v in profile.items()}}
