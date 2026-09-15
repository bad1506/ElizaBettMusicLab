from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

import telegram_auth
import web_auth

CURRENT_USER: ContextVar[dict[str, Any] | None] = ContextVar("current_user", default=None)
_PUBLIC_PATHS = {"/", "/health", "/auth/telegram", "/auth/register", "/auth/login", "/public/yandex-chart", "/sona-chat"}
_MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "100")) * 1024 * 1024
_RATE_LOCK = threading.Lock()
_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def max_upload_bytes() -> int:
    return _MAX_UPLOAD_BYTES


def current_user() -> dict[str, Any]:
    user = CURRENT_USER.get()
    return user or {"id": "local", "first_name": "Local"}


def current_user_id() -> str:
    return str(current_user().get("id") or "local")


def is_local_request(request: Request) -> bool:
    host = request.client.host if request.client else ""
    return host in {"127.0.0.1", "::1", "localhost"}


def _rate_limit(bucket: str, limit: int, window: int = 60) -> bool:
    now = time.monotonic()
    with _RATE_LOCK:
        q = _RATE_BUCKETS[bucket]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


def security_middleware(app):
    @app.middleware("http")
    async def _security(request: Request, call_next):
        path = request.url.path
        token = None

        if request.method == "OPTIONS":
            response = await call_next(request)
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            return response

        if path == "/sona-chat":
            host = request.client.host if request.client else "unknown"
            if not _rate_limit(f"chat-ip:{host}", 20):
                return JSONResponse({"detail": "Слишком много сообщений. Попробуйте через минуту."}, status_code=429, headers={"Retry-After": "60"})
        elif path not in _PUBLIC_PATHS:
            init_data = request.headers.get("X-Telegram-Init-Data", "").strip()
            web_token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            allow_local = os.getenv("ALLOW_LOCAL_UNAUTH", "false").lower() == "true"
            if not init_data and not web_token and not (allow_local and is_local_request(request)):
                return JSONResponse({"detail": "Authentication required"}, status_code=401)
            if init_data:
                try:
                    max_age = int(os.getenv("TELEGRAM_INIT_DATA_MAX_AGE", "3600"))
                    data = telegram_auth.validate_init_data(init_data, max_age=max_age)
                    token = CURRENT_USER.set(data.get("user") or {})
                except telegram_auth.TelegramAuthError:
                    return JSONResponse({"detail": "Invalid or expired Telegram authentication"}, status_code=401)
            elif web_token:
                user = web_auth.get_user(web_token)
                if not user:
                    return JSONResponse({"detail": "Invalid or expired account session"}, status_code=401)
                token = CURRENT_USER.set({"id": user["id"], "first_name": user["name"], "last_name": "", "username": user["email"]})
            else:
                token = CURRENT_USER.set({"id": "local", "first_name": "Local"})

            uid = current_user_id()
            if path in {"/upload", "/reference"}:
                limit = 10
            elif path in {"/master", "/stems", "/production/run"}:
                limit = 6
            elif path.startswith("/songwriter") or path == "/chat":
                limit = 30
            else:
                limit = 120
            if not _rate_limit(f"{uid}:{path}", limit):
                if token:
                    CURRENT_USER.reset(token)
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429, headers={"Retry-After": "60"})

            if path in {"/upload", "/reference"}:
                content_length = request.headers.get("content-length")
                if content_length:
                    try:
                        if int(content_length) > _MAX_UPLOAD_BYTES + 1024 * 1024:
                            if token:
                                CURRENT_USER.reset(token)
                            return JSONResponse({"detail": "Uploaded file is too large"}, status_code=413)
                    except ValueError:
                        pass

        try:
            response = await call_next(request)
        finally:
            if token:
                CURRENT_USER.reset(token)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        return response

    return _security


def user_storage(base: Path) -> dict[str, Path]:
    raw = current_user_id()
    safe_id = "".join(ch for ch in raw if ch.isalnum() or ch in "-_")[:80] or "local"
    root = base / "user_data" / safe_id
    dirs = {"root": root, "input": root / "mastering_input", "output": root / "optimizer_output", "separated": root / "separated", "reference": root / "reference", "project": root / "project_data"}
    for directory in dirs.values():
        directory.mkdir(parents=True, exist_ok=True)
    return dirs


def resolve_user_file(base: Path, kind: str, relative_path: str) -> Path | None:
    dirs = user_storage(base)
    key = {"input": "input", "optimizer_output": "output", "separated": "separated", "reference": "reference", "project_data": "project"}.get(kind)
    if not key:
        return None
    root = dirs[key].resolve()
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        return None
    return candidate
