from __future__ import annotations

import json
from urllib.request import Request, urlopen

from fastapi import HTTPException, Request as FastAPIRequest
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

class ActivityRequest(BaseModel):
    kind: str = Field(default="activity", max_length=40)
    title: str = Field(min_length=1, max_length=160)
    detail: str = Field(default="", max_length=1000)

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

@app.get("/auth/me")
def auth_me(request: FastAPIRequest):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    user = web_auth.get_user(token)
    if not user:
        raise HTTPException(401, "Invalid or expired account session")
    return {"ok": True, "user": user, "history": web_auth.get_activity(user["id"])}

@app.get("/auth/history")
def auth_history(request: FastAPIRequest):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    user = web_auth.get_user(token)
    if not user:
        raise HTTPException(401, "Invalid or expired account session")
    return {"ok": True, "history": web_auth.get_activity(user["id"])}

@app.post("/auth/history")
def auth_history_add(request: FastAPIRequest, activity: ActivityRequest):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    user = web_auth.get_user(token)
    if not user:
        raise HTTPException(401, "Invalid or expired account session")
    web_auth.add_activity(user["id"], activity.kind, activity.title, activity.detail)
    return {"ok": True}

YANDEX_CHART_URL = "https://api.music.yandex.net/landing3/chart/russia"

def _fetch_chart() -> dict:
    request = Request(YANDEX_CHART_URL, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/136 Safari/537.36 SonaMusicLab/1.0",
        "X-Yandex-Music-Device": "os=web; os_version=1; manufacturer=SØNA; model=Web; clid=; device_id=sona; uuid=sona-web",
        "Referer": "https://music.yandex.ru/",
        "Origin": "https://music.yandex.ru",
    })
    with urlopen(request, timeout=15) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"upstream status {response.status}")
        return json.loads(response.read())

@app.get("/public/yandex-chart")
def public_yandex_chart():
    try:
        return _fetch_chart()
    except Exception as exc:
        raise HTTPException(502, "Yandex Music chart is temporarily unavailable") from exc

__all__ = ["app"]
