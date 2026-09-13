from pathlib import Path
import json
import numpy as np
import soundfile as sf

import mastering


# ============================================================
# MASTER QUALITY CONTROL 2.1
# Goal-based evaluation of automatic processing
# ============================================================


PROBLEM_ALIASES = {
    "relative_harshness": "harshness",
    "relative_mud": "mud",
    "relative_low_air": "low_air",
    "relative_excess_sub": "excess_sub",

    # direct names
    "harshness": "harshness",
    "mud": "mud",
    "low_air": "low_air",
    "excess_sub": "excess_sub",

    # additional aliases for future analyzers
    "excess_bass": "excess_bass",
    "low_mid": "mud",
    "presence": "harshness",
}


PROBLEM_BANDS = {
    "harshness": "presence_2000_6000",
    "mud": "low_mid_150_500",
    "low_air": "air_12000_20000",
    "excess_sub": "sub_20_60",
    "excess_bass": "bass_60_150",
}


def _safe_float(value, default=0.0):
    try:
        value = float(value)
        if not np.isfinite(value):
            return default
        return value
    except Exception:
        return default


def _load_audio(path):
    audio, sr = sf.read(str(path), always_2d=True)
    audio = audio.astype(np.float64)

    if audio.shape[1] > 2:
        audio = audio[:, :2]

    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)

    return audio, sr


def _analysis(path):
    audio, sr = _load_audio(path)
    return mastering.analyze_master(audio, sr)


def _score_peak(peak_db):
    peak_db = _safe_float(peak_db)

    if peak_db <= -1.0:
        return 100.0

    if peak_db <= -0.5:
        return 90.0

    if peak_db <= 0.0:
        return 65.0

    return 20.0


def _score_dynamics(crest_db):
    crest_db = _safe_float(crest_db)

    if crest_db >= 8.0:
        return 100.0

    if crest_db >= 6.0:
        return 90.0

    if crest_db >= 4.0:
        return 75.0

    if crest_db >= 3.0:
        return 60.0

    return 40.0


def _score_stereo(stereo_width_db, correlation):
    width = _safe_float(stereo_width_db)
    corr = _safe_float(correlation)

    score = 100.0

    if corr < 0.0:
        score -= 40.0
    elif corr < 0.2:
        score -= 20.0

    if width < -18.0:
        score -= 25.0

    return max(0.0, min(100.0, score))


def _normalize_problem(problem):
    if not problem:
        return None

    problem = str(problem).strip().lower()

    return PROBLEM_ALIASES.get(problem, problem)


def _get_band_data(analysis):
    bands = analysis.get("band_energy_percent", {})

    if not isinstance(bands, dict):
        return {}

    return {
        str(k): _safe_float(v)
        for k, v in bands.items()
    }


def _band_value(analysis, band):
    bands = _get_band_data(analysis)
    return _safe_float(bands.get(band, 0.0))


def _evaluate_goal(problem, original, final, gain_db=0.0):
    normalized = _normalize_problem(problem)

    band = PROBLEM_BANDS.get(normalized)

    if band is None:
        return {
            "problem": problem,
            "normalized_problem": normalized,
            "band": None,
            "status": "unknown",
            "score": 50.0,
            "delta": 0.0,
            "gain_db": _safe_float(gain_db),
            "reason": "Неизвестный тип цели",
        }

    original_value = _band_value(original, band)
    final_value = _band_value(final, band)

    if original_value <= 1e-9:
        delta = 0.0
    else:
        delta = (final_value - original_value) / original_value

    # --------------------------------------------------------
    # Excess / problematic energy
    # Goal: REDUCE the problematic band
    # --------------------------------------------------------

    if normalized in {
        "harshness",
        "mud",
        "excess_sub",
        "excess_bass",
    }:

        if delta <= -0.20:
            status = "solved"
            score = 100.0

        elif delta <= -0.10:
            status = "improved"
            score = 90.0

        elif delta <= -0.03:
            status = "slightly_improved"
            score = 75.0

        elif delta < 0.03:
            status = "unchanged"
            score = 50.0

        elif delta < 0.10:
            status = "worse"
            score = 30.0

        else:
            status = "much_worse"
            score = 10.0

    # --------------------------------------------------------
    # Low air
    # Goal: INCREASE air
    # --------------------------------------------------------

    elif normalized == "low_air":

        if delta >= 0.20:
            status = "solved"
            score = 100.0

        elif delta >= 0.10:
            status = "improved"
            score = 90.0

        elif delta >= 0.03:
            status = "slightly_improved"
            score = 75.0

        elif delta > -0.03:
            status = "unchanged"
            score = 50.0

        elif delta > -0.10:
            status = "worse"
            score = 30.0

        else:
            status = "much_worse"
            score = 10.0

    else:
        status = "unknown"
        score = 50.0

    return {
        "problem": problem,
        "normalized_problem": normalized,
        "band": band,
        "status": status,
        "score": round(float(score), 2),
        "delta": round(float(delta), 6),
        "gain_db": round(_safe_float(gain_db), 3),
        "original_value": round(float(original_value), 4),
        "final_value": round(float(final_value), 4),
        "reason": _goal_reason(normalized, status, delta),
    }


def _goal_reason(problem, status, delta):
    pct = abs(delta) * 100.0

    if problem in {
        "harshness",
        "mud",
        "excess_sub",
        "excess_bass",
    }:
        if delta < 0:
            return f"Проблемная полоса уменьшилась на {pct:.1f}%."
        if delta > 0:
            return f"Проблемная полоса увеличилась на {pct:.1f}%."
        return "Изменение проблемной полосы практически отсутствует."

    if problem == "low_air":
        if delta > 0:
            return f"Air увеличился на {pct:.1f}%."
        if delta < 0:
            return f"Air уменьшился на {pct:.1f}%."
        return "Изменение Air практически отсутствует."

    return "Цель не распознана."


def _extract_plan_problems(processing_plan):
    problems = []

    if not processing_plan:
        return problems

    steps = processing_plan.get("steps", [])

    for step in steps:
        problem = step.get("problem")

        if not problem:
            # Fallback: action name can identify the problem
            action = step.get("action", "")

            action_map = {
                "dynamic_presence_control": "relative_harshness",
                "dynamic_low_mid_control": "relative_mud",
                "dynamic_sub_control": "relative_excess_sub",
                "air_shelf": "relative_low_air",
            }

            problem = action_map.get(action)

        if problem:
            normalized = _normalize_problem(problem)

            if normalized not in [p[0] for p in problems]:
                problems.append(
                    (
                        normalized,
                        _safe_float(step.get("gain_db", 0.0)),
                    )
                )

    return problems


def evaluate_goals(original, final, processing_plan=None):
    problems = _extract_plan_problems(processing_plan)

    goals = []

    for problem, gain_db in problems:
        result = _evaluate_goal(
            problem,
            original,
            final,
            gain_db,
        )

        goals.append(result)

    return goals


def _overall_verdict(score, warnings):
    if warnings:
        if score >= 85:
            return "acceptable_with_warnings"

        if score >= 65:
            return "needs_review"

        return "poor"

    if score >= 90:
        return "excellent"

    if score >= 75:
        return "acceptable"

    if score >= 60:
        return "needs_review"

    return "poor"


def compare_files(original_path, processed_path, processing_plan=None):
    original = _analysis(original_path)
    final = _analysis(processed_path)

    goals = evaluate_goals(
        original,
        final,
        processing_plan,
    )

    peak_score = _score_peak(
        final.get("peak_dbfs", 0.0)
    )

    dynamics_score = _score_dynamics(
        final.get("crest_factor_db", 0.0)
    )

    stereo_score = _score_stereo(
        final.get("stereo_width_db", 0.0),
        final.get("mono_correlation", 1.0),
    )

    if goals:
        goal_score = float(
            np.mean(
                [
                    _safe_float(g["score"], 50.0)
                    for g in goals
                ]
            )
        )
    else:
        goal_score = 100.0

    warnings = []

    for goal in goals:
        if goal["status"] in {
            "worse",
            "much_worse",
        }:
            warnings.append(
                f"{goal['problem']}: {goal['status']}"
            )

    # A severe regression gets an additional penalty.
    regression_penalty = 0.0

    for goal in goals:
        if goal["status"] == "much_worse":
            regression_penalty += 15.0
        elif goal["status"] == "worse":
            regression_penalty += 5.0

    overall_score = (
        goal_score * 0.45
        + peak_score * 0.20
        + dynamics_score * 0.20
        + stereo_score * 0.15
        - regression_penalty
    )

    overall_score = max(
        0.0,
        min(100.0, overall_score),
    )

    return {
        "original": original,
        "processed": final,
        "evaluation": {
            "overall_score": round(overall_score, 2),
            "verdict": _overall_verdict(
                overall_score,
                warnings,
            ),
            "goal_score": round(goal_score, 2),
            "peak_score": round(peak_score, 2),
            "dynamics_score": round(dynamics_score, 2),
            "stereo_score": round(stereo_score, 2),
            "goals": goals,
            "warnings": warnings,
        },
    }


def save_report(report, path):
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