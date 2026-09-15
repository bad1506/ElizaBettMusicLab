"""Public Yandex Music chart adapter for SØNA.

The Yandex endpoint is public chart data but can vary by region/network. We keep a
small server-side cache and try the documented API first, then its known public
CORS proxy, so the website does not depend on a user's browser region.
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
PRIMARY = "https://api.music.yandex.net/landing3/chart/russia"
PROXY = "https://yandex-music-cors-proxy.onrender.com/https://api.music.yandex.net:443/landing3/chart/russia"


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


def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Expose a stable SØNA shape while retaining the raw Yandex payload."""
    root = payload.get("result", payload)
    chart_info = root.get("chart") if isinstance(root, dict) else None
    tracks = []
    if isinstance(chart_info, dict):
        tracks = chart_info.get("tracks") or []
        if not tracks and isinstance(chart_info.get("chart"), dict):
            tracks = chart_info["chart"].get("tracks") or []
    if not tracks and isinstance(root, dict):
        tracks = root.get("tracks") or root.get("items") or []
    return {"ok": True, "source": "Yandex Music", "updated_at": int(time.time()), "items": tracks[:50], "result": payload.get("result", payload)}


def register_yandex_chart(app) -> None:
    @app.get("/public/yandex-chart")
    def yandex_chart():
        cache = _load_cache()
        now = time.time()
        if cache and now - float(cache.get("saved_at", 0)) < CACHE_TTL:
            return _normalize(cache["payload"])

        last_error: Exception | None = None
        for upstream in (PRIMARY, PROXY):
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
