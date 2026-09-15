from __future__ import annotations

import json
from urllib.request import Request, urlopen

from fastapi import HTTPException

from api_secure import app


YANDEX_CHART_URL = "https://api.music.yandex.net/landing3/chart/russia"


@app.get("/public/yandex-chart")
def public_yandex_chart():
    """Small server-side proxy for the public Yandex Music Russia chart.

    The browser cannot reliably call the Yandex endpoint because of CORS and
    device-header requirements, so the public web shell consumes this route.
    """
    request = Request(
        YANDEX_CHART_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "SonaMusicLab/1.0",
            "X-Yandex-Music-Device": "os=unknown; os_version=unknown; manufacturer=unknown; model=unknown; clid=; device_id=unknown; uuid=unknown",
        },
    )
    try:
        with urlopen(request, timeout=8) as response:
            if response.status < 200 or response.status >= 300:
                raise HTTPException(502, "Yandex Music chart upstream error")
            payload = response.read()
        return json.loads(payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, "Yandex Music chart is temporarily unavailable") from exc


__all__ = ["app"]
