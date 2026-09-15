from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any

BASE_URL = os.getenv("PROMPTS_CHAT_API_URL", "https://prompts.chat/api/prompts")


def search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Ищет публичные prompts.chat без обязательного API-ключа."""
    query = query.strip()[:500]
    if not query:
        return []
    limit = max(1, min(int(limit), 10))
    params = urllib.parse.urlencode({"q": query, "perPage": limit})
    request = urllib.request.Request(
        f"{BASE_URL}?{params}",
        headers={"Accept": "application/json", "User-Agent": "SonaMusicLab/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []

    items = payload.get("prompts", payload.get("data", []))
    if not isinstance(items, list):
        return []
    return [item for item in items[:limit] if isinstance(item, dict)]
