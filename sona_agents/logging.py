from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


SENSITIVE_KEYS = {"authorization", "api_key", "token", "password", "secret"}


def _safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: "[REDACTED]" if k.lower() in SENSITIVE_KEYS else _safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe(v) for v in value[:20]]
    if isinstance(value, str):
        return value[:2000]
    return value


def log_agent_call(*, agent: str, skill: str, ok: bool, latency_ms: int, error: str | None = None, metadata: dict[str, Any] | None = None) -> None:
    """Пишет компактный JSONL-аудит без секретов и содержимого пользовательского запроса."""
    directory = Path(os.getenv("SONA_AGENT_LOG_DIR", ".sona/logs"))
    try:
        directory.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": time.time(),
            "agent": agent,
            "skill": skill,
            "ok": ok,
            "latency_ms": latency_ms,
            "error": error[:500] if error else None,
            "metadata": _safe(metadata or {}),
        }
        with (directory / "agent-calls.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        # Логирование не должно ломать пользовательский запрос.
        return
