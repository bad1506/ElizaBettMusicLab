from __future__ import annotations

import json
from urllib.request import Request, urlopen

from fastapi import HTTPException

from api_secure import app


YANDEX_CHART_URLS = (
    "https://yandex-music-cors-proxy.onrender.com/https://api.music.yandex.net:443/landing3/chart/russia",
    "https://api.music.yandex.net/landing3/chart/russia",
)


def _fetch_chart(url: str) -> dict:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "SonaMusicLab/1.0",
            "X-Yandex-Music-Device": "os=unknown; os_version=unknown; manufacturer=unknown; model=unknown; clid=; device_id=unknown; uuid=unknown",
        },
    )
    with urlopen(request, timeout=10) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"upstream status {response.status}")
        return json.loads(response.read())


@app.get("/public/yandex-chart")
def public_yandex_chart():
    """Public server-side Yandex Music Russia chart proxy with fallback."""
    last_error: Exception | None = None
    for url in YANDEX_CHART_URLS:
        try:
            return _fetch_chart(url)
        except Exception as exc:
            last_error = exc
    raise HTTPException(502, "Yandex Music chart is temporarily unavailable") from last_error


__all__ = ["app"]
