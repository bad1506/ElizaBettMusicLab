import math


# ============================================================
# ELIZA BETT MUSIC LAB
# DECISION ENGINE 5.3
#
# Главная задача:
# превратить множество 10-секундных наблюдений
# в небольшое количество музыкально осмысленных решений.
# ============================================================


ACTION_META = {
    "dynamic_sub_control": {
        "title": "Sub 20–60 Hz",
        "frequency": "20–60 Hz",
        "mode": "dynamic",
        "max_gain_db": -2.5,
    },

    "dynamic_bass_control": {
        "title": "Bass 60–150 Hz",
        "frequency": "60–150 Hz",
        "mode": "dynamic",
        "max_gain_db": -3.0,
    },

    "dynamic_low_mid_control": {
        "title": "Low-mid 150–500 Hz",
        "frequency": "150–500 Hz",
        "mode": "dynamic",
        "max_gain_db": -2.5,
    },

    "dynamic_presence_control": {
        "title": "Presence 2–6 kHz",
        "frequency": "2–6 kHz",
        "mode": "dynamic",
        "max_gain_db": -2.5,
    },

    "air_shelf": {
        "title": "Air 12–20 kHz",
        "frequency": "12–20 kHz",
        "mode": "shelf",
        "max_gain_db": 1.5,
    },
}


# ============================================================
# PROBLEM → ACTION
# ============================================================

PROBLEM_TO_ACTION = {
    "relative_excess_sub":
        "dynamic_sub_control",

    "relative_excess_bass":
        "dynamic_bass_control",

    "relative_mud":
        "dynamic_low_mid_control",

    "relative_harshness":
        "dynamic_presence_control",

    "relative_low_air":
        "air_shelf",
}


# ============================================================
# HELPERS
# ============================================================

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _smooth_severity(raw):
    """
    Преобразует относительное превышение
    в более музыкально разумную шкалу 0..1.
    """

    raw = max(
        0.0,
        _safe_float(raw)
    )

    return 1.0 - math.exp(
        -1.35 * raw
    )


def _problem_severity(item, problem):
    relative = item.get(
        "relative",
        {}
    )

    if problem == "relative_excess_sub":
        value = relative.get(
            "sub_20_60",
            1.0
        )

        raw = max(
            0.0,
            _safe_float(value) - 1.0
        )

    elif problem == "relative_excess_bass":
        value = relative.get(
            "bass_60_150",
            1.0
        )

        raw = max(
            0.0,
            _safe_float(value) - 1.0
        )

    elif problem == "relative_mud":
        value = relative.get(
            "low_mid_150_500",
            1.0
        )

        raw = max(
            0.0,
            _safe_float(value) - 1.0
        )

    elif problem == "relative_harshness":
        value = relative.get(
            "presence_2000_6000",
            1.0
        )

        raw = max(
            0.0,
            _safe_float(value) - 1.0
        )

    elif problem == "relative_low_air":
        value = relative.get(
            "air_12000_20000",
            1.0
        )

        raw = max(
            0.0,
            1.0 - _safe_float(value)
        )

    else:
        raw = 0.0

    return _smooth_severity(
        raw
    )


def _context(item):
    """
    Определяет приблизительный музыкальный контекст
    по относительной громкости сегмента.
    """

    relative_rms = _safe_float(
        item.get(
            "relative_rms",
            1.0
        ),
        1.0,
    )

    if relative_rms >= 1.20:
        return "chorus_or_peak"

    if relative_rms <= 0.75:
        return "intro_or_break"

    if relative_rms <= 0.90:
        return "verse_or_quiet"

    return "verse_or_transition"


def _context_adjustment(
    action,
    context,
):
    """
    Корректировка уверенности с учётом музыкального контекста.
    """

    # В припеве сильный bass может быть частью аранжировки.
    if action == "dynamic_bass_control":

        if context == "chorus_or_peak":
            return 0.78

    # Presence в припеве тоже может быть намеренной.
    if action == "dynamic_presence_control":

        if context == "chorus_or_peak":
            return 0.78

    # В тихом intro недостаток air не всегда проблема.
    if action == "air_shelf":

        if context == "intro_or_break":
            return 0.75

    return 1.0


def _suggested_gain(
    action,
    severity,
):
    meta = ACTION_META[
        action
    ]

    maximum = float(
        meta["max_gain_db"]
    )

    severity = max(
        0.0,
        min(
            1.0,
            _safe_float(severity)
        )
    )

    if action == "air_shelf":

        gain = maximum * severity

        # Air никогда не поднимаем агрессивно.
        gain = min(
            1.5,
            gain
        )

        return round(
            gain,
            2
        )

    gain = maximum * severity

    return round(
        max(
            maximum,
            gain
        ),
        2
    )


def _priority_label(
    priority
):
    """
    Человеческая классификация приоритета.
    """

    priority = _safe_float(
        priority
    )

    if priority >= 0.78:
        return "высокий"

    if priority >= 0.58:
        return "средний"

    if priority >= 0.35:
        return "низкий"

    return "наблюдение"


def _merge_ranges(
    items,
    max_gap=10.1,
):
    """
    Объединяет соседние проблемные сегменты.
    """

    if not items:
        return []

    ordered = sorted(
        items,
        key=lambda x:
        x["time_start"]
    )

    ranges = []

    start = ordered[0][
        "time_start"
    ]

    end = ordered[0][
        "time_end"
    ]

    for item in ordered[1:]:

        current_start = item[
            "time_start"
        ]

        current_end = item[
            "time_end"
        ]

        if current_start <= (
            end + max_gap
        ):

            end = max(
                end,
                current_end
            )

        else:

            ranges.append({
                "time_start":
                    round(start, 2),

                "time_end":
                    round(end, 2),
            })

            start = current_start
            end = current_end

    ranges.append({
        "time_start":
            round(start, 2),

        "time_end":
            round(end, 2),
    })

    return ranges


def _dominant_context(
    items
):
    """
    Определяет наиболее частый контекст.
    """

    counts = {}

    for item in items:

        context = item.get(
            "context",
            "unknown"
        )

        counts[context] = (
            counts.get(
                context,
                0
            ) + 1
        )

    if not counts:
        return "unknown"

    return max(
        counts,
        key=counts.get
    )


# ============================================================
# MAIN DECISION ENGINE
# ============================================================

def build_decisions(
    timeline
):
    """
    Главная функция.

    На вход:
        timeline["segments"]

    На выход:
        НЕ отдельные решения каждого сегмента,

        а сгруппированные музыкальные решения.
    """

    timeline = timeline or {}

    segments = timeline.get(
        "segments",
        []
    )

    if not segments:
        return []

    # --------------------------------------------------------
    # ШАГ 1
    # Собираем наблюдения по каждому типу проблемы.
    # --------------------------------------------------------

    groups = {}

    for item in segments:

        problems = item.get(
            "problems",
            []
        )

        if not problems:
            continue

        for problem in problems:

            action = PROBLEM_TO_ACTION.get(
                problem
            )

            if not action:
                continue

            severity = _problem_severity(
                item,
                problem
            )

            if severity <= 0:
                continue

            context = _context(
                item
            )

            confidence = (
                0.55
                + severity * 0.45
            )

            confidence *= (
                _context_adjustment(
                    action,
                    context
                )
            )

            confidence = min(
                1.0,
                confidence
            )

            if action not in groups:

                groups[action] = []

            groups[action].append({
                "time_start":
                    _safe_float(
                        item.get(
                            "time_start"
                        )
                    ),

                "time_end":
                    _safe_float(
                        item.get(
                            "time_end"
                        )
                    ),

                "severity":
                    severity,

                "confidence":
                    confidence,

                "context":
                    context,
            })

    # --------------------------------------------------------
    # ШАГ 2
    # Создаём итоговое решение для каждого диапазона.
    # --------------------------------------------------------

    decisions = []

    total_segments = max(
        1,
        len(segments)
    )

    for action, items in groups.items():

        meta = ACTION_META[
            action
        ]

        occurrence_count = len(
            items
        )

        # ----------------------------------------------------
        # Сила максимального проявления.
        # ----------------------------------------------------

        max_severity = max(
            item["severity"]
            for item in items
        )

        # ----------------------------------------------------
        # Средняя сила проблемы.
        # ----------------------------------------------------

        avg_severity = (
            sum(
                item["severity"]
                for item in items
            )
            / occurrence_count
        )

        # ----------------------------------------------------
        # Persistence:
        # насколько проблема повторяется.
        # ----------------------------------------------------

        persistence = min(
            1.0,
            occurrence_count
            / max(
                3.0,
                total_segments * 0.35
            )
        )

        # ----------------------------------------------------
        # Средняя уверенность.
        # ----------------------------------------------------

        avg_confidence = (
            sum(
                item["confidence"]
                for item in items
            )
            / occurrence_count
        )

        # ----------------------------------------------------
        # Итоговая уверенность.
        #
        # Не даём одному пику автоматически
        # стать "100%".
        # ----------------------------------------------------

        confidence = (
            avg_confidence * 0.65
            + persistence * 0.35
        )

        confidence = min(
            1.0,
            confidence
        )

        # ----------------------------------------------------
        # Итоговая severity.
        #
        # Смешиваем максимальное проявление
        # и среднее поведение.
        # ----------------------------------------------------

        severity = (
            max_severity * 0.60
            + avg_severity * 0.40
        )

        severity = min(
            1.0,
            severity
        )

        # ----------------------------------------------------
        # Priority.
        # ----------------------------------------------------

        priority = (
            severity * 0.60
            + confidence * 0.25
            + persistence * 0.15
        )

        priority = min(
            1.0,
            priority
        )

        # ----------------------------------------------------
        # Если проблема редкая и слабая,
        # не называем её высокой.
        # ----------------------------------------------------

        if (
            occurrence_count == 1
            and severity < 0.70
        ):
            priority *= 0.65

        # ----------------------------------------------------
        # Музыкальный контекст.
        # ----------------------------------------------------

        dominant_context = _dominant_context(
            items
        )

        # ----------------------------------------------------
        # Временные диапазоны.
        # ----------------------------------------------------

        ranges = _merge_ranges(
            items
        )

        # ----------------------------------------------------
        # Рекомендуемое изменение.
        # ----------------------------------------------------

        suggested_gain = _suggested_gain(
            action,
            severity
        )

        # ----------------------------------------------------
        # Безопасность.
        # ----------------------------------------------------

        safety = (
            "bounded_dynamic_processing"
            if meta["mode"] == "dynamic"
            else "bounded_shelf"
        )

        # ----------------------------------------------------
        # Итоговый объект.
        # ----------------------------------------------------

        decision = {
            "action":
                action,

            "problem":
                next(
                    (k for k, v in PROBLEM_TO_ACTION.items() if v == action),
                    None
                ),

            "label":
                meta["title"],

            "title":
                meta["title"],

            "frequency":
                meta["frequency"],

            "mode":
                meta["mode"],

            "severity":
                round(
                    severity,
                    3
                ),

            "confidence":
                round(
                    confidence,
                    3
                ),

            "priority":
                round(
                    priority,
                    3
                ),

            "priority_label":
                _priority_label(
                    priority
                ),

            "suggested_gain_db":
                suggested_gain,

            "musical_context":
                dominant_context,

            "occurrences":
                occurrence_count,

            "time_ranges":
                ranges,

            "safety":
                safety,
        }

        decisions.append(
            decision
        )

    # --------------------------------------------------------
    # ШАГ 3
    # Сортируем по приоритету.
    # --------------------------------------------------------

    decisions.sort(
        key=lambda item: (
            item["priority"],
            item["severity"],
            item["confidence"],
        ),
        reverse=True,
    )

    return decisions