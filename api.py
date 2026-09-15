from __future__ import annotations

import json
from urllib.request import Request, urlopen

from fastapi import HTTPException
from pydantic import BaseModel, Field

from api_secure import app
import chat_api
import web_auth

# The web application is the primary client. Telegram remains optional.
chat_api.register(app)

class AuthRequest(BaseModel):
    name: str = Field(default="", max_length=120)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)

@app.post("/auth/register")
def auth_register(request: AuthRequest):
    try:
        return {"ok": True, **web_auth.register(request.name, request.email, request.password)}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post("/auth/login")
def auth_login(request: AuthRequest):
    try:
        return {"ok": True, **web_auth.login(request.email, request.password)}
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from exc

YANDEX_CHART_URLS = (
    "https://yandex-music-cors-proxy.onrender.com/https://api.music.yandex.net:443/landing3/chart/russia",
    "https://api.music.yandex.net/landing3/chart/russia",
)

def _fetch_chart(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "SonaMusicLab/1.0"})
    with urlopen(request, timeout=10) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"upstream status {response.status}")
        return json.loads(response.read())

@app.get("/public/yandex-chart")
def public_yandex_chart():
    last_error: Exception | None = None
    for url in YANDEX_CHART_URLS:
        try:
            return _fetch_chart(url)
        except Exception as exc:
            last_error = exc
    raise HTTPException(502, "Yandex Music chart is temporarily unavailable") from last_error

__all__ = ["app"]
