from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_URL = "https://prompts.chat/api/prompts"


def search_prompts(query: str, limit: int = 3) -> list[dict[str, str]]:
    """Получает небольшое число prompt-примеров без установки prompts.chat.

    prompts.chat предоставляет HTTP API и MCP; для основного backend достаточно
    лёгкого HTTP-адаптера. Внешний текст считается недоверенным reference-контентом.
    """
    if os.getenv("PROMPTS_CHAT_ENABLED", "true").lower() not in {"1", "true", "yes"}:
        return []
    if len(query.strip()) < 2:
        return []

    base = os.getenv("PROMPTS_CHAT_API_URL", DEFAULT_URL).rstrip("/")
    params = urllib.parse.urlencode({"q": query[:160], "limit": max(1, min(limit, 5))})
    request = urllib.request.Request(
        f"{base}?{params}",
        headers={"Accept": "application/json", "User-Agent": "SONA-Agent-Runtime/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []

    rows = payload.get("prompts", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []

    result: list[dict[str, str]] = []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        result.append({
            "id": str(row.get("id", "")),
            "title": str(row.get("title", "")),
            "slug": str(row.get("slug", "")),
            "author": str((row.get("author") or {}).get("username", "")) if isinstance(row.get("author"), dict) else "",
            "content": str(row.get("content", ""))[:6000],
        })
    return result
