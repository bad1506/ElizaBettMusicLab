"""Public Yandex Music chart adapter for SØNA.

Yandex exposes the public chart through landing3 endpoints. SØNA tries the
specific Russia chart first and the landing3 chart block as a compatibility
fallback, keeping a short server-side cache so the public site does not depend
on browser CORS or a user's Yandex session.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

CACHE_TTL = 10 * 60
UPSTREAMS = (
    "https://api.music.yandex.net/landing3/chart/russia",
    "https://api.music.yandex.net/landing3?blocks=chart",
    "https://yandex-music-cors-proxy.onrender.com/https://api.music.yandex.net:443/landing3/chart/russia",
    "https://yandex-music-cors-proxy.onrender.com/https://api.music.yandex.net:443/landing3?blocks=chart",
)


def _cache_file() -> Path:
    base = Path(os.getenv("SONA_DATA_DIR", "/tmp/sona"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "yandex_chart_russia.json"


def _request(url: str) -> dict[str, Any]:
    req = Request(url, headers={
        "User-Agent": "SØNA-Music-Intelligence/1.0",
        "Accept": "application/json",
        "X-Yandex-Music-Device": "os=unknown; os_version=unknown; manufacturer=unknown; model=unknown; clid=; device_id=unknown; uuid=sona-public",
    })
    with urlopen(req, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def _load_cache() -> dict[str, Any] | None:
    path = _cache_file()
    try:
        data = json.loads(path.read_text("utf-8"))
        if data.get("payload"):
            return data
    except Exception:
        return None
    return None


def _save_cache(payload: dict[str, Any]) -> None:
    path = _cache_file()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"saved_at": time.time(), "payload": payload}, ensure_ascii=False), "utf-8")
    tmp.replace(path)


def _track_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("tracks", "items", "chart", "playlist"):
            found = _track_list(value.get(key))
            if found:
                return found
    return []


def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Expose a stable SØNA shape while retaining the raw Yandex payload."""
    root = payload.get("result", payload)
    tracks: list[Any] = []
    if isinstance(root, dict):
        tracks = _track_list(root.get("chart"))
        if not tracks:
            tracks = _track_list(root.get("blocks"))
        if not tracks:
            tracks = _track_list(root.get("items"))
        if not tracks:
            tracks = _track_list(root.get("tracks"))

    # landing3 can wrap the chart in a block object; search one level deeper.
    if not tracks and isinstance(root, dict):
        for value in root.values():
            candidate = _track_list(value)
            if candidate and any(isinstance(item, dict) and (item.get("track") or item.get("title")) for item in candidate):
                tracks = candidate
                break

    return {
        "ok": True,
        "source": "Yandex Music",
        "updated_at": int(time.time()),
        "items": tracks[:50],
        "result": payload.get("result", payload),
    }


def register_yandex_chart(app) -> None:
    @app.get("/public/yandex-chart")
    def yandex_chart():
        cache = _load_cache()
        now = time.time()
        if cache and now - float(cache.get("saved_at", 0)) < CACHE_TTL:
            return _normalize(cache["payload"])

        last_error: Exception | None = None
        for upstream in UPSTREAMS:
            try:
                payload = _request(upstream)
                normalized = _normalize(payload)
                if normalized["items"]:
                    _save_cache(payload)
                    return normalized
                last_error = RuntimeError("Yandex returned an empty chart")
            except (HTTPError, URLError, TimeoutError, ValueError, RuntimeError) as exc:
                last_error = exc

        if cache and cache.get("payload"):
            return _normalize(cache["payload"])
        raise HTTPException(status_code=503, detail=f"Yandex chart unavailable: {type(last_error).__name__ if last_error else 'upstream_error'}")
