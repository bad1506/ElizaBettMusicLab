from __future__ import annotations

from fastapi import HTTPException, Request as FastAPIRequest, Response
from pydantic import BaseModel, Field

from api_secure import app
import chat_api
import web_auth
import yandex_public

# The web application is the primary client. Telegram remains optional.
chat_api.register(app)
yandex_public.register_yandex_chart(app)

SESSION_COOKIE = "sona_session"

class AuthRequest(BaseModel):
    name: str = Field(default="", max_length=120)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)

class ActivityRequest(BaseModel):
    kind: str = Field(default="activity", max_length=40)
    title: str = Field(min_length=1, max_length=160)
    detail: str = Field(default="", max_length=1000)


def _token(request: FastAPIRequest) -> str:
    header = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    return header or request.cookies.get(SESSION_COOKIE, "")


def _finish(response: Response, data: dict) -> dict:
    token = data.get("token")
    if token:
        response.set_cookie(SESSION_COOKIE, token, max_age=60 * 60 * 24 * 30, httponly=True, secure=True, samesite="lax", path="/")
    return {"ok": True, **data}

@app.post("/auth/register")
def auth_register(request: AuthRequest, response: Response):
    try:
        return _finish(response, web_auth.register(request.name, request.email, request.password))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post("/auth/login")
def auth_login(request: AuthRequest, response: Response):
    try:
        return _finish(response, web_auth.login(request.email, request.password))
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from exc

@app.post("/auth/logout")
def auth_logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}

@app.get("/auth/me")
def auth_me(request: FastAPIRequest):
    user = web_auth.get_user(_token(request))
    if not user:
        raise HTTPException(401, "Invalid or expired account session")
    return {"ok": True, "user": user, "history": web_auth.get_activity(user["id"])}

@app.get("/auth/history")
def auth_history(request: FastAPIRequest):
    user = web_auth.get_user(_token(request))
    if not user:
        raise HTTPException(401, "Invalid or expired account session")
    return {"ok": True, "history": web_auth.get_activity(user["id"])}

@app.post("/auth/history")
def auth_history_add(request: FastAPIRequest, activity: ActivityRequest):
    user = web_auth.get_user(_token(request))
    if not user:
        raise HTTPException(401, "Invalid or expired account session")
    web_auth.add_activity(user["id"], activity.kind, activity.title, activity.detail)
    return {"ok": True}

__all__ = ["app"]
