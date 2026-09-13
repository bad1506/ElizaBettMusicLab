import json
import math
import os
import urllib.error
import urllib.request


# ============================================================
# ELIZA BETT MUSIC LAB
# AI ENGINEER 2.2
# ============================================================


ACTION_META = {
    "dynamic_sub_control": {
        "title": "Sub 20–60 Hz",
        "max_gain_db": -2.5,
    },
    "dynamic_bass_control": {
        "title": "Bass 60–150 Hz",
        "max_gain_db": -3.0,
    },
    "dynamic_low_mid_control": {
        "title": "Low-mid 150–500 Hz",
        "max_gain_db": -2.5,
    },
    "dynamic_presence_control": {
        "title": "Presence 2–6 kHz",
        "max_gain_db": -2.5,
    },
    "air_shelf": {
        "title": "Air 12–20 kHz",
        "max_gain_db": 1.5,
    },
}


# ============================================================
# HELPERS
# ============================================================

def _safe_float(value, default=None):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _percent(value):
    value = _safe_float(value, 0.0)
    return round(value * 100)


def _priority_label(priority):
    priority = _safe_float(priority, 0.0)

    if priority >= 0.78:
        return "высокий"
    if priority >= 0.50:
        return "средний"
    if priority >= 0.30:
        return "низкий"

    return "наблюдение"


def _severity_label(severity):
    severity = _safe_float(severity, 0.0)

    if severity >= 0.75:
        return "высокая"
    if severity >= 0.50:
        return "средняя"
    if severity >= 0.25:
        return "низкая"

    return "минимальная"


# ============================================================
# INTELLIGENT MIX ANALYSIS
# ============================================================

def analyze_mix_intelligently(
    analysis=None,
    decisions=None,
    master_report=None,
):
    """
    Формирует структурированный анализ микса.

    ВАЖНО:
    Используются реальные ключи adaptive_analyze():
        lufs
        rms_dbfs
        peak_dbfs
        true_peak_dbfs
        crest_factor_db
        stereo_width_db
        mono_correlation
        lr_balance_db
        band_energy_percent
        flags
        recommendations
    """

    analysis = analysis or {}
    decisions = decisions or []
    master_report = master_report or {}

    result = {
        "measurements": {},
        "problems": [],
        "recommendations": [],
        "summary": "",
    }

    # --------------------------------------------------------
    # REAL MEASUREMENTS
    # --------------------------------------------------------

    measurements = result["measurements"]

    field_map = {
        "lufs": "lufs",
        "rms_dbfs": "rms_dbfs",
        "peak_dbfs": "peak_dbfs",
        "true_peak_dbfs": "true_peak_dbfs",
        "crest_factor_db": "crest_factor_db",
        "stereo_width_db": "stereo_width_db",
        "mono_correlation": "mono_correlation",
        "lr_balance_db": "lr_balance_db",
    }

    for output_key, input_key in field_map.items():
        if input_key in analysis:
            measurements[output_key] = analysis[input_key]

    # --------------------------------------------------------
    # DYNAMICS
    # --------------------------------------------------------

    crest = _safe_float(
        analysis.get("crest_factor_db")
    )

    if crest is not None:

        if crest < 7:
            result["problems"].append({
                "title": "Слишком плотная динамика",
                "reason": (
                    f"Crest factor {crest:.1f} dB. "
                    "Возможна сильная компрессия или лимитирование."
                ),
                "severity": "high",
            })

        elif crest < 9:
            result["problems"].append({
                "title": "Плотная динамика",
                "reason": (
                    f"Crest factor {crest:.1f} dB. "
                    "Дополнительную компрессию стоит применять осторожно."
                ),
                "severity": "medium",
            })

        elif crest > 15:
            result["recommendations"].append(
                f"Crest factor {crest:.1f} dB: "
                "динамика достаточно широкая. "
                "Сохраняйте естественные пики."
            )

    # --------------------------------------------------------
    # TRUE PEAK
    # --------------------------------------------------------

    true_peak = _safe_float(
        analysis.get("true_peak_dbfs")
    )

    if true_peak is not None:

        if true_peak > -0.5:
            result["problems"].append({
                "title": "Недостаточный запас True Peak",
                "reason": (
                    f"True Peak {true_peak:.1f} dBTP. "
                    "Пик слишком близко к 0 dBTP."
                ),
                "severity": "high",
            })

        elif true_peak > -1.0:
            result["problems"].append({
                "title": "True Peak выше безопасного ориентира",
                "reason": (
                    f"True Peak {true_peak:.1f} dBTP. "
                    "Для финального мастера лучше оставить около -1 dBTP."
                ),
                "severity": "medium",
            })

    # --------------------------------------------------------
    # STEREO
    # --------------------------------------------------------

    correlation = _safe_float(
        analysis.get("mono_correlation")
    )

    if correlation is not None:

        if correlation < 0.20:
            result["problems"].append({
                "title": "Очень широкое стерео",
                "reason": (
                    f"Mono correlation {correlation:.2f}. "
                    "Высокий риск проблем при mono-суммировании."
                ),
                "severity": "high",
            })

        elif correlation < 0.50:
            result["problems"].append({
                "title": "Широкое стерео",
                "reason": (
                    f"Mono correlation {correlation:.2f}. "
                    "Проверьте mono compatibility."
                ),
                "severity": "medium",
            })

        elif correlation > 0.95:
            result["recommendations"].append(
                f"Mono correlation {correlation:.2f}: "
                "микс практически моно."
            )

    # --------------------------------------------------------
    # L/R BALANCE
    # --------------------------------------------------------

    balance = _safe_float(
        analysis.get("lr_balance_db")
    )

    if balance is not None:

        if abs(balance) >= 2.0:
            result["problems"].append({
                "title": "Заметный дисбаланс L/R",
                "reason": (
                    f"Баланс каналов {balance:+.1f} dB. "
                    "Проверьте панораму и уровень каналов."
                ),
                "severity": "medium",
            })

        elif abs(balance) >= 1.0:
            result["recommendations"].append(
                f"L/R balance {balance:+.1f} dB: "
                "есть небольшой перекос каналов."
            )

    # --------------------------------------------------------
    # FLAGS FROM ADAPTIVE ANALYZER
    # --------------------------------------------------------

    flags = analysis.get(
        "flags",
        []
    )

    flag_titles = {
        "excess_sub": "Избыток Sub 20–60 Hz",
        "excess_bass": "Избыток Bass 60–150 Hz",
        "low_air": "Недостаток Air 12–20 kHz",
    }

    for flag in flags:

        if flag in flag_titles:

            result["problems"].append({
                "title": flag_titles[flag],
                "reason": (
                    "Adaptive Analyzer обнаружил "
                    "отклонение спектрального баланса."
                ),
                "severity": "medium",
            })

    # --------------------------------------------------------
    # DECISION ENGINE
    # --------------------------------------------------------

    for decision in decisions[:5]:

        action = decision.get(
            "action"
        )

        title = decision.get(
            "title",
            ACTION_META.get(
                action,
                {}
            ).get(
                "title",
                action or "Обработка"
            ),
        )

        priority = _safe_float(
            decision.get("priority"),
            0.0,
        )

        confidence = _safe_float(
            decision.get("confidence"),
            0.0,
        )

        severity = _safe_float(
            decision.get("severity"),
            0.0,
        )

        gain = decision.get(
            "suggested_gain_db"
        )

        result["problems"].append({
            "title": title,
            "action": action,
            "priority": _priority_label(priority),
            "priority_value": priority,
            "confidence": confidence,
            "severity": severity,
            "suggested_gain_db": gain,
            "time_ranges": decision.get(
                "time_ranges",
                []
            ),
            "occurrences": decision.get(
                "occurrences",
                0,
            ),
        })

    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    unique = {}

    for problem in result["problems"]:

        key = (
            problem.get("action"),
            problem.get("title"),
        )

        if key not in unique:
            unique[key] = problem

        else:
            current = unique[key]

            current["priority_value"] = max(
                _safe_float(
                    current.get("priority_value"),
                    0,
                ),
                _safe_float(
                    problem.get("priority_value"),
                    0,
                ),
            )

            current["confidence"] = max(
                _safe_float(
                    current.get("confidence"),
                    0,
                ),
                _safe_float(
                    problem.get("confidence"),
                    0,
                ),
            )

            current["severity"] = max(
                _safe_float(
                    current.get("severity"),
                    0,
                ),
                _safe_float(
                    problem.get("severity"),
                    0,
                ),
            )

    result["problems"] = list(
        unique.values()
    )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    result["problems"].sort(
        key=lambda item: (
            _safe_float(
                item.get("priority_value"),
                0,
            ),
            _safe_float(
                item.get("severity"),
                0,
            ),
            _safe_float(
                item.get("confidence"),
                0,
            ),
        ),
        reverse=True,
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    if result["problems"]:

        top = result["problems"][0]

        result["summary"] = (
            f"Главный приоритет: "
            f"{top.get('title', 'обработка')} "
            f"({top.get('priority', 'наблюдение')})."
        )

    else:

        result["summary"] = (
            "Критичных автоматических проблем "
            "по доступным измерениям не обнаружено."
        )

    return result


# ============================================================
# LOCAL ADVICE
# ============================================================

def build_local_advice(
    analysis=None,
    decisions=None,
    master_report=None,
):
    analysis = analysis or {}
    decisions = decisions or []
    master_report = master_report or {}

    advice = []

    # --------------------------------------------------------
    # DYNAMICS
    # --------------------------------------------------------

    crest = _safe_float(
        analysis.get("crest_factor_db")
    )

    if crest is not None:

        if crest < 7:
            advice.append(
                "Динамика сильно сжата: "
                f"crest factor {crest:.1f} dB."
            )

        elif crest < 9:
            advice.append(
                "Динамика плотная: "
                f"crest factor {crest:.1f} dB."
            )

    # --------------------------------------------------------
    # TRUE PEAK
    # --------------------------------------------------------

    true_peak = _safe_float(
        analysis.get("true_peak_dbfs")
    )

    if true_peak is not None:

        if true_peak > -0.5:
            advice.append(
                "True Peak слишком близко к 0 dBTP. "
                "Рекомендуется ceiling около -1 dBTP."
            )

        elif true_peak > -1.0:
            advice.append(
                "True Peak выше безопасного ориентира. "
                "Для финального мастера лучше оставить около -1 dBTP."
            )

    # --------------------------------------------------------
    # STEREO
    # --------------------------------------------------------

    correlation = _safe_float(
        analysis.get("mono_correlation")
    )

    if correlation is not None:

        if correlation < 0.20:
            advice.append(
                "Стерео очень широкое. "
                "Обязательно проверьте mono compatibility."
            )

        elif correlation < 0.50:
            advice.append(
                "Стерео широкое. "
                "Проверьте совместимость микса в mono."
            )

    # --------------------------------------------------------
    # DECISIONS
    # --------------------------------------------------------

    seen = set()

    for decision in decisions:

        title = decision.get(
            "title",
            decision.get(
                "action",
                "Обработка"
            ),
        )

        if title in seen:
            continue

        seen.add(title)

        priority = _safe_float(
            decision.get("priority"),
            0.0,
        )

        confidence = _safe_float(
            decision.get("confidence"),
            0.0,
        )

        gain = decision.get(
            "suggested_gain_db"
        )

        label = decision.get(
            "priority_label"
        )

        if not label:
            label = _priority_label(
                priority
            )

        text = (
            f"{title}: "
            f"приоритет {label}, "
            f"уверенность {round(confidence * 100)}%"
        )

        if gain is not None:

            gain = float(gain)

            if gain > 0:
                text += (
                    f", ориентир +{gain:.1f} dB"
                )
            else:
                text += (
                    f", ориентир {gain:.1f} dB"
                )

        ranges = decision.get(
            "time_ranges",
            []
        )

        if ranges:

            first = ranges[0]

            start = float(
                first.get(
                    "time_start",
                    0,
                )
            )

            end = float(
                first.get(
                    "time_end",
                    0,
                )
            )

            text += (
                f". Основная зона "
                f"{start:.0f}–{end:.0f} сек."
            )

        occurrences = decision.get(
            "occurrences",
            0,
        )

        if occurrences > 1:

            text += (
                f". Повторяется в "
                f"{occurrences} сегментах"
            )

        advice.append(
            text + "."
        )

        if len(advice) >= 5:
            break

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    if not advice:

        advice.append(
            "Критичных автоматических проблем "
            "не обнаружено. "
            "Микс можно дорабатывать точечно."
        )

    return advice


# ============================================================
# LOCAL ANSWER
# ============================================================

def answer_local(
    question,
    analysis=None,
    decisions=None,
    master_report=None,
):
    question = (
        question or ""
    ).lower().strip()

    analysis = analysis or {}
    decisions = decisions or []
    master_report = master_report or {}

    # --------------------------------------------------------
    # MIX ANALYSIS
    # --------------------------------------------------------

    if (
        "что сейчас не так" in question
        or "что не так" in question
        or "анализ" in question
        or "проблем" in question
        or "микс" in question
    ):

        intelligent = analyze_mix_intelligently(
            analysis,
            decisions,
            master_report,
        )

        lines = [
            "АНАЛИЗ AI ENGINEER"
        ]

        # ----------------------------------------------------
        # MEASUREMENTS
        # ----------------------------------------------------

        measurements = []

        lufs = _safe_float(
            analysis.get("lufs")
        )

        rms = _safe_float(
            analysis.get("rms_dbfs")
        )

        peak = _safe_float(
            analysis.get("peak_dbfs")
        )

        true_peak = _safe_float(
            analysis.get("true_peak_dbfs")
        )

        crest = _safe_float(
            analysis.get("crest_factor_db")
        )

        correlation = _safe_float(
            analysis.get("mono_correlation")
        )

        stereo_width = _safe_float(
            analysis.get("stereo_width_db")
        )

        balance = _safe_float(
            analysis.get("lr_balance_db")
        )

        if lufs is not None:
            measurements.append(
                f"LUFS {lufs:.1f}"
            )

        if rms is not None:
            measurements.append(
                f"RMS {rms:.1f} dBFS"
            )

        if peak is not None:
            measurements.append(
                f"Peak {peak:.1f} dBFS"
            )

        if true_peak is not None:
            measurements.append(
                f"True Peak {true_peak:.1f} dBTP"
            )

        if crest is not None:
            measurements.append(
                f"Crest {crest:.1f} dB"
            )

        if correlation is not None:
            measurements.append(
                f"Mono correlation {correlation:.2f}"
            )

        if stereo_width is not None:
            measurements.append(
                f"Stereo width {stereo_width:.1f} dB"
            )

        if balance is not None:
            measurements.append(
                f"L/R {balance:+.1f} dB"
            )

        if measurements:

            lines.append(
                "Измерения: "
                + " | ".join(measurements)
            )

        # ----------------------------------------------------
        # PROBLEMS
        # ----------------------------------------------------

        lines.append("")
        lines.append(
            "ГЛАВНЫЕ ПРОБЛЕМЫ"
        )

        problems = intelligent.get(
            "problems",
            []
        )

        if not problems:

            lines.append(
                "Критичных проблем по доступным "
                "измерениям не обнаружено."
            )

        else:

            for index, problem in enumerate(
                problems[:5],
                start=1,
            ):

                title = problem.get(
                    "title",
                    "Обработка",
                )

                priority = problem.get(
                    "priority",
                    "наблюдение",
                )

                confidence = _percent(
                    problem.get(
                        "confidence",
                        0,
                    )
                )

                gain = problem.get(
                    "suggested_gain_db"
                )

                text = (
                    f"{index}. "
                    f"{title} "
                    f"[{priority}]"
                )

                if confidence:

                    text += (
                        f" — уверенность "
                        f"{confidence}%"
                    )

                if gain is not None:

                    gain = float(gain)

                    if gain > 0:
                        text += (
                            f", ориентир +{gain:.1f} dB"
                        )
                    else:
                        text += (
                            f", ориентир {gain:.1f} dB"
                        )

                ranges = problem.get(
                    "time_ranges",
                    []
                )

                if ranges:

                    first = ranges[0]

                    start = float(
                        first.get(
                            "time_start",
                            0,
                        )
                    )

                    end = float(
                        first.get(
                            "time_end",
                            0,
                        )
                    )

                    text += (
                        f", зона "
                        f"{start:.0f}–{end:.0f} сек."
                    )

                occurrences = problem.get(
                    "occurrences",
                    0,
                )

                if occurrences > 1:

                    text += (
                        f", {occurrences} сегментов"
                    )

                lines.append(
                    text
                )

        # ----------------------------------------------------
        # RECOMMENDATIONS
        # ----------------------------------------------------

        recommendations = intelligent.get(
            "recommendations",
            []
        )

        if recommendations:

            lines.append("")
            lines.append(
                "РЕКОМЕНДАЦИИ"
            )

            for recommendation in recommendations[:3]:

                lines.append(
                    f"• {recommendation}"
                )

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        lines.append("")
        lines.append(
            "ВЫВОД"
        )

        lines.append(
            intelligent.get(
                "summary",
                "Анализ завершён.",
            )
        )

        return "\n".join(lines)

    # --------------------------------------------------------
    # VOCAL
    # --------------------------------------------------------

    if (
        "вокал" in question
        or "голос" in question
        or "voice" in question
    ):

        return (
            "Для полноценного анализа вокала нужен "
            "Vocal Intelligence: pitch, диапазон, "
            "стабильность, проблемные участки "
            "и спектр вокальной дорожки."
        )

    # --------------------------------------------------------
    # MASTERING
    # --------------------------------------------------------

    if (
        "мастеринг" in question
        or "master" in question
        or "громк" in question
        or "lufs" in question
    ):

        lines = [
            "МАСТЕРИНГ AI ENGINEER"
        ]

        lufs = _safe_float(
            analysis.get("lufs")
        )

        true_peak = _safe_float(
            analysis.get("true_peak_dbfs")
        )

        if lufs is not None:

            lines.append(
                f"Текущий уровень: {lufs:.1f} LUFS."
            )

        if true_peak is not None:

            lines.append(
                f"True Peak: {true_peak:.1f} dBTP."
            )

        lines.append(
            "Безопасная отправная точка: "
            "-10.5 LUFS и -1.0 dBTP."
        )

        lines.append(
            "Цепочка: адаптивный EQ → динамика → "
            "сатурация → loudness → true-peak limiter."
        )

        return "\n".join(lines)

    # --------------------------------------------------------
    # BASS
    # --------------------------------------------------------

    if (
        "бас" in question
        or "низ" in question
        or "sub" in question
    ):

        for decision in decisions:

            action = decision.get(
                "action"
            )

            if action in (
                "dynamic_sub_control",
                "dynamic_bass_control",
            ):

                title = decision.get(
                    "title",
                    "Низкие частоты",
                )

                gain = decision.get(
                    "suggested_gain_db"
                )

                if gain is not None:

                    return (
                        f"{title}: обнаружено "
                        "поведение, которое стоит контролировать. "
                        f"Ориентир {float(gain):.1f} dB. "
                        "Предпочтительно динамическое управление, "
                        "а не постоянный сильный EQ-срез."
                    )

        return (
            "По текущим решениям Decision Engine "
            "отдельной значимой проблемы в низком "
            "диапазоне не обнаружено."
        )

    # --------------------------------------------------------
    # DEFAULT
    # --------------------------------------------------------

    advice = build_local_advice(
        analysis,
        decisions,
        master_report,
    )

    return "\n".join(
        [
            "AI ENGINEER",
            "",
            *[
                f"• {item}"
                for item in advice[:6]
            ],
        ]
    )


# ============================================================
# OPENAI
# ============================================================

def ask_openai(
    question,
    context,
):
    """
    Подключение OpenAI Responses API.

    Если OPENAI_API_KEY не установлен,
    возвращается None и используется локальный AI.
    """

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:
        return None

    question = (
        question or ""
    ).strip()

    if not question:
        return None

    context = context or {}

    system_prompt = """
Ты AI Engineer внутри Eliza Bett Music Lab.

Ты анализируешь музыкальные миксы как инженер
по сведению и мастеринг-инженер.

ПРАВИЛА:

1. Используй только реальные данные из контекста.
2. Не выдумывай измерения.
3. Не называй слабую проблему критичной.
4. Не повторяй одинаковые проблемы.
5. Decision Engine уже группирует повторяющиеся проблемы.
6. Приоритет учитывает выраженность, уверенность и повторяемость.
7. Если проблема появляется только в отдельных участках,
   предпочитай Dynamic EQ или динамическую обработку.
8. Не рекомендуй большой EQ-срез без достаточных оснований.
9. Предпочитай небольшие безопасные изменения.
10. Для мастеринга ориентир True Peak около -1 dBTP.
11. Не утверждай, что прослушал звук, если есть только измерения.
12. Если данных недостаточно — прямо скажи об этом.
13. Отвечай по-русски.
14. Сначала объясни проблему.
15. Затем объясни причину.
16. Затем предложи действие.
17. Не создавай повторяющиеся пункты.
18. Учитывай весь переданный контекст.
"""

    payload = {
        "model": os.getenv(
            "OPENAI_MODEL",
            "gpt-5.6",
        ),
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": system_prompt,
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "КОНТЕКСТ MUSIC LAB:\n"
                            + json.dumps(
                                context,
                                ensure_ascii=False,
                                indent=2,
                                default=str,
                            )
                            + "\n\n"
                            "ВОПРОС:\n"
                            + question
                        ),
                    }
                ],
            },
        ],
    }

    body = json.dumps(
        payload,
        ensure_ascii=False,
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        method="POST",
        headers={
            "Authorization": (
                f"Bearer {api_key}"
            ),
            "Content-Type": "application/json",
        },
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=60,
        ) as response:

            raw = response.read().decode(
                "utf-8"
            )

        data = json.loads(
            raw
        )

        output_text = data.get(
            "output_text"
        )

        if output_text:

            return output_text.strip()

        output = data.get(
            "output",
            []
        )

        texts = []

        for item in output:

            for part in item.get(
                "content",
                []
            ):

                text = part.get(
                    "text"
                )

                if text:
                    texts.append(
                        text
                    )

        if texts:

            return "\n".join(
                texts
            ).strip()

        return None

    except urllib.error.HTTPError as error:

        try:

            error_body = error.read().decode(
                "utf-8",
                errors="ignore",
            )

            print(
                "OpenAI HTTP error:",
                error.code,
                error_body,
            )

        except Exception:
            pass

        return None

    except Exception as error:

        print(
            "OpenAI request error:",
            error,
        )

        return None