"""
Processing Planner v1
Eliza Bett Music Lab

Decision Engine -> Processing Plan

Задача:
- превратить решения Decision Engine в безопасный план обработки;
- не применять максимальные значения автоматически;
- учитывать priority, severity, confidence;
- сохранять time_ranges;
- ограничивать глубину обработки;
- отделять corrective processing от enhancement.
"""

from __future__ import annotations

from typing import Any, Dict, List


PLANNER_VERSION = "1.0"


# ------------------------------------------------------------
# Безопасные пределы обработки
# ------------------------------------------------------------

SAFE_LIMITS = {
    "dynamic_sub_control": {
        "min_gain_db": -2.0,
        "max_gain_db": 0.0,
        "attack_ms": 25.0,
        "release_ms": 120.0,
    },

    "dynamic_bass_control": {
        "min_gain_db": -2.5,
        "max_gain_db": 0.0,
        "attack_ms": 30.0,
        "release_ms": 140.0,
    },

    "dynamic_low_mid_control": {
        "min_gain_db": -2.5,
        "max_gain_db": 0.0,
        "attack_ms": 35.0,
        "release_ms": 160.0,
    },

    "dynamic_presence_control": {
        "min_gain_db": -2.5,
        "max_gain_db": 0.0,
        "attack_ms": 15.0,
        "release_ms": 100.0,
    },

    "air_shelf": {
        "min_gain_db": 0.0,
        "max_gain_db": 1.5,
    },
}


# ------------------------------------------------------------
# Приоритет
# ------------------------------------------------------------

PRIORITY_MULTIPLIER = {
    "высокий": 1.0,
    "средний": 0.75,
    "низкий": 0.5,
}


# ------------------------------------------------------------
# Вспомогательные функции
# ------------------------------------------------------------

def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    return max(minimum, min(maximum, value))


def _round(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


def _safe_ranges(decision: Dict[str, Any]) -> List[Dict[str, float]]:
    ranges = decision.get("time_ranges", [])

    if not isinstance(ranges, list):
        return []

    result = []

    for item in ranges:
        if not isinstance(item, dict):
            continue

        start = _float(item.get("time_start"))
        end = _float(item.get("time_end"))

        if end <= start:
            continue

        result.append(
            {
                "time_start": _round(max(0.0, start), 3),
                "time_end": _round(max(start, end), 3),
            }
        )

    return result


# ------------------------------------------------------------
# Расчёт безопасного количества обработки
# ------------------------------------------------------------

def _calculate_gain(
    action: str,
    suggested_gain: float,
    severity: float,
    confidence: float,
    priority_label: str,
) -> float:

    limits = SAFE_LIMITS.get(action)

    if not limits:
        return 0.0

    priority_multiplier = PRIORITY_MULTIPLIER.get(
        priority_label,
        0.5,
    )

    # Чем выше уверенность и severity,
    # тем ближе мы подходим к предложенному значению.
    strength = (
        0.35
        + 0.35 * _clamp(severity, 0.0, 1.0)
        + 0.30 * _clamp(confidence, 0.0, 1.0)
    )

    strength *= priority_multiplier

    gain = suggested_gain * strength

    return _round(
        _clamp(
            gain,
            limits["min_gain_db"],
            limits["max_gain_db"],
        ),
        2,
    )


# ------------------------------------------------------------
# Создание одного processing step
# ------------------------------------------------------------

def _build_step(decision: Dict[str, Any]) -> Dict[str, Any]:

    action = str(
        decision.get("action", "none")
    )

    if action not in SAFE_LIMITS:
        return {}

    severity = _clamp(
        _float(decision.get("severity")),
        0.0,
        1.0,
    )

    confidence = _clamp(
        _float(decision.get("confidence")),
        0.0,
        1.0,
    )

    priority = str(
        decision.get(
            "priority_label",
            "низкий",
        )
    )

    suggested_gain = _float(
        decision.get(
            "suggested_gain_db",
            0.0,
        )
    )

    gain_db = _calculate_gain(
        action,
        suggested_gain,
        severity,
        confidence,
        priority,
    )

    ranges = _safe_ranges(decision)

    meta = SAFE_LIMITS[action]

    step = {
        "action": action,

        "problem": decision.get(
            "problem"
        ),

        "title": decision.get(
            "title",
            decision.get(
                "label",
                action,
            ),
        ),

        "frequency": decision.get(
            "frequency"
        ),

        "mode": decision.get(
            "mode",
            "dynamic",
        ),

        "priority": priority,

        "severity": _round(
            severity
        ),

        "confidence": _round(
            confidence
        ),

        "gain_db": gain_db,

        "time_ranges": ranges,

        "occurrences": int(
            decision.get(
                "occurrences",
                len(ranges),
            )
            or 0
        ),

        "parameters": {},

        "safety": "bounded_processing",
    }

    # --------------------------------------------------------
    # Dynamic processing
    # --------------------------------------------------------

    if action.startswith("dynamic_"):

        step["parameters"] = {
            "max_reduction_db": abs(
                _round(
                    gain_db,
                    2,
                )
            ),

            "attack_ms": meta.get(
                "attack_ms",
                30.0,
            ),

            "release_ms": meta.get(
                "release_ms",
                120.0,
            ),

            "dynamic_only": True,

            "apply_only_in_ranges": True,
        }

    # --------------------------------------------------------
    # Air shelf
    # --------------------------------------------------------

    elif action == "air_shelf":

        step["parameters"] = {
            "gain_db": _round(
                gain_db,
                2,
            ),

            "dynamic_only": False,

            "apply_only_in_ranges": True,

            "shelf_type": "high_shelf",

            "frequency_hz": 12000.0,

            "q": 0.7,
        }

    return step


# ------------------------------------------------------------
# Основная функция
# ------------------------------------------------------------

def build_processing_plan(
    decisions: List[Dict[str, Any]],
) -> Dict[str, Any]:

    if not isinstance(decisions, list):
        decisions = []

    steps = []

    for decision in decisions:

        if not isinstance(decision, dict):
            continue

        step = _build_step(decision)

        if step:
            steps.append(step)

    # Сначала высокий приоритет.
    priority_order = {
        "высокий": 0,
        "средний": 1,
        "низкий": 2,
    }

    steps.sort(
        key=lambda item: (
            priority_order.get(
                item.get(
                    "priority",
                    "низкий",
                ),
                3,
            ),
            -_float(
                item.get(
                    "priority_score",
                    item.get(
                        "severity",
                        0.0,
                    ),
                )
            ),
        )
    )

    # --------------------------------------------------------
    # Определяем общую стратегию
    # --------------------------------------------------------

    if not steps:
        strategy = "minimal_processing"

    elif any(
        step["priority"] == "высокий"
        for step in steps
    ):
        strategy = "corrective_first"

    else:
        strategy = "gentle_enhancement"

    return {
        "planner_version": PLANNER_VERSION,

        "strategy": strategy,

        "steps": steps,

        "steps_count": len(steps),

        "safety": {
            "max_dynamic_reduction_db": 2.5,
            "max_air_boost_db": 1.5,
            "dynamic_processing": True,
            "range_limited_processing": True,
            "avoid_global_cuts": True,
        },

        "workflow": [
            "analyze",
            "corrective_processing",
            "re_analyze",
            "final_tone_shaping",
            "limiter",
            "true_peak_check",
        ],
    }


# ------------------------------------------------------------
# Удобный алиас
# ------------------------------------------------------------

def create_plan(
    decisions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return build_processing_plan(decisions)


# ------------------------------------------------------------
# Самотест
# ------------------------------------------------------------

if __name__ == "__main__":

    test_decisions = [
        {
            "action": "dynamic_presence_control",
            "problem": "relative_harshness",
            "title": "Presence 2–6 kHz",
            "frequency": "2–6 kHz",
            "mode": "dynamic",
            "severity": 0.97,
            "confidence": 0.893,
            "priority": 0.918,
            "priority_label": "высокий",
            "suggested_gain_db": -2.42,
            "occurrences": 5,
            "time_ranges": [
                {
                    "time_start": 10.0,
                    "time_end": 20.0,
                }
            ],
        }
    ]

    result = build_processing_plan(
        test_decisions
    )

    print(
        "PROCESSING PLANNER",
        PLANNER_VERSION,
    )

    print(
        "STRATEGY:",
        result["strategy"],
    )

    print(
        "STEPS:",
        result["steps_count"],
    )

    for step in result["steps"]:
        print(
            step["action"],
            "| gain:",
            step["gain_db"],
            "| ranges:",
            step["time_ranges"],
        )