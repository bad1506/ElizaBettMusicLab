from __future__ import annotations

import json
import re
from urllib.request import Request, urlopen

from fastapi import HTTPException
from pydantic import BaseModel, Field

from api_secure import app
import web_auth

YANDEX_CHART_URLS = (
    "https://yandex-music-cors-proxy.onrender.com/https://api.music.yandex.net:443/landing3/chart/russia",
    "https://api.music.yandex.net/landing3/chart/russia",
)


def _fetch_chart(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "SonaMusicLab/1.0", "X-Yandex-Music-Device": "os=unknown; os_version=unknown; manufacturer=unknown; model=unknown; clid=; device_id=unknown; uuid=unknown"})
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


class WebAuthRequest(BaseModel):
    name: str = Field(default="", min_length=0, max_length=80)
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=128)


_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _auth_response(data: dict) -> dict:
    return {"ok": True, "token": data["token"], "expires_at": data["expires_at"], "user": data["user"]}


@app.post("/auth/register")
def register_account(request: WebAuthRequest):
    name = request.name.strip()
    email = request.email.strip().lower()
    if len(name) < 2:
        raise HTTPException(400, "Укажи имя")
    if not _EMAIL_RE.match(email):
        raise HTTPException(400, "Некорректный email")
    try:
        return _auth_response(web_auth.register(name, email, request.password))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/auth/login")
def login_account(request: WebAuthRequest):
    email = request.email.strip().lower()
    try:
        return _auth_response(web_auth.login(email, request.password))
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from exc


__all__ = ["app"]
