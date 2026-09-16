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
from storage_backend import get_storage_backend

CURRENT_USER: ContextVar[dict[str, Any] | None] = ContextVar("current_user", default=None)
_PUBLIC_PATHS = {"/", "/health", "/auth/telegram", "/auth/register", "/auth/login", "/public/yandex-chart", "/agents/skills"}
_MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "100")) * 1024 * 1024
_RATE_LOCK = threading.Lock(); _RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def max_upload_bytes() -> int: return _MAX_UPLOAD_BYTES

def current_user() -> dict[str, Any]: return CURRENT_USER.get() or {"id": "local", "first_name": "Local"}

def current_user_id() -> str: return str(current_user().get("id") or "local")
def is_local_request(request: Request) -> bool: return (request.client.host if request.client else "") in {"127.0.0.1", "::1", "localhost"}


def _rate_limit(bucket: str, limit: int, window: int = 60) -> bool:
    now = time.monotonic()
    with _RATE_LOCK:
        q = _RATE_BUCKETS[bucket]
        while q and now - q[0] > window: q.popleft()
        if len(q) >= limit: return False
        q.append(now); return True


def _workspace_snapshot(root: Path) -> dict[str, tuple[int, int]]:
    snapshot: dict[str, tuple[int, int]] = {}
    if not root.exists():
        return snapshot
    for path in root.rglob("*"):
        if not path.is_file() or path.name == ".sona-storage.lock" or ".sona_storage_meta" in path.parts:
            continue
        try:
            stat = path.stat(); snapshot[str(path)] = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            continue
    return snapshot


def _persist_workspace(base: Path, root: Path, before: dict[str, tuple[int, int]]) -> None:
    backend = get_storage_backend(base)
    after = _workspace_snapshot(root)
    changed = [Path(path) for path, stamp in after.items() if before.get(path) != stamp]
    for path in changed:
        backend.sync_file(current_user_id(), path)


def security_middleware(app):
    @app.middleware("http")
    async def _security(request: Request, call_next):
        path = request.url.path; token = None; workspace_root: Path | None = None; workspace_before: dict[str, tuple[int, int]] = {}
        if request.method == "OPTIONS":
            response = await call_next(request); response.headers.setdefault("X-Content-Type-Options", "nosniff"); return response
        if path == "/sona-chat":
            init_data = request.headers.get("X-Telegram-Init-Data", "").strip(); web_token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            if not init_data and not web_token:
                allow_local = os.getenv("ALLOW_LOCAL_UNAUTH", "false").lower() == "true"
                if not (allow_local and is_local_request(request)):
                    return JSONResponse({"detail": "Authentication required"}, status_code=401)
            elif init_data:
                try: data = telegram_auth.validate_init_data(init_data, max_age=int(os.getenv("TELEGRAM_INIT_DATA_MAX_AGE", "3600"))); token = CURRENT_USER.set(data.get("user") or {})
                except telegram_auth.TelegramAuthError: return JSONResponse({"detail": "Invalid or expired Telegram authentication"}, status_code=401)
            else:
                user = web_auth.get_user(web_token)
                if not user: return JSONResponse({"detail": "Invalid or expired account session"}, status_code=401)
                token = CURRENT_USER.set({"id": user["id"], "first_name": user["name"], "last_name": "", "username": user["email"]})
            uid = current_user_id()
            if not _rate_limit(f"{uid}:/sona-chat", 30):
                if token: CURRENT_USER.reset(token)
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429, headers={"Retry-After": "60"})
        elif path not in _PUBLIC_PATHS:
            init_data = request.headers.get("X-Telegram-Init-Data", "").strip(); web_token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip(); allow_local = os.getenv("ALLOW_LOCAL_UNAUTH", "false").lower() == "true"
            if not init_data and not web_token and not (allow_local and is_local_request(request)): return JSONResponse({"detail": "Authentication required"}, status_code=401)
            if init_data:
                try: data = telegram_auth.validate_init_data(init_data, max_age=int(os.getenv("TELEGRAM_INIT_DATA_MAX_AGE", "3600"))); token = CURRENT_USER.set(data.get("user") or {})
                except telegram_auth.TelegramAuthError: return JSONResponse({"detail": "Invalid or expired Telegram authentication"}, status_code=401)
            elif web_token:
                user = web_auth.get_user(web_token)
                if not user: return JSONResponse({"detail": "Invalid or expired account session"}, status_code=401)
                token = CURRENT_USER.set({"id": user["id"], "first_name": user["name"], "last_name": "", "username": user["email"]})
            else: token = CURRENT_USER.set({"id": "local", "first_name": "Local"})
            uid = current_user_id(); limit = 10 if path in {"/upload", "/reference"} else 6 if path in {"/master", "/stems", "/production/run"} else 30 if path.startswith("/songwriter") or path == "/chat" else 120
            if not _rate_limit(f"{uid}:{path}", limit):
                if token: CURRENT_USER.reset(token)
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429, headers={"Retry-After": "60"})
            if path in {"/upload", "/reference"}:
                content_length = request.headers.get("content-length")
                if content_length:
                    try:
                        if int(content_length) > _MAX_UPLOAD_BYTES + 1024 * 1024:
                            if token: CURRENT_USER.reset(token)
                            return JSONResponse({"detail": "Uploaded file is too large"}, status_code=413)
                    except ValueError: pass
        if token or path == "/sona-chat" or path not in _PUBLIC_PATHS:
            try:
                backend = get_storage_backend(Path(__file__).resolve().parent)
                workspace_root = backend.user_root(current_user_id())
                backend.hydrate(current_user_id())
                workspace_before = _workspace_snapshot(workspace_root)
            except Exception:
                if token: CURRENT_USER.reset(token)
                return JSONResponse({"detail": "User storage unavailable"}, status_code=503)
        try:
            response = await call_next(request)
            if workspace_root is not None and response.status_code < 400:
                try:
                    _persist_workspace(Path(__file__).resolve().parent, workspace_root, workspace_before)
                except Exception:
                    return JSONResponse({"detail": "User storage synchronization failed"}, status_code=503)
        finally:
            if token: CURRENT_USER.reset(token)
        for key, value in {"X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY","Referrer-Policy":"no-referrer","Permissions-Policy":"camera=(), microphone=(), geolocation=()","Cross-Origin-Resource-Policy":"same-site","Content-Security-Policy":"default-src 'none'; frame-ancestors 'none'"}.items(): response.headers.setdefault(key, value)
        return response
    return _security


def user_storage(base: Path) -> dict[str, Path]:
    backend = get_storage_backend(base)
    user_id = current_user_id()
    root = backend.user_root(user_id)
    backend.hydrate(user_id)
    dirs = {"root":root,"input":root/"mastering_input","output":root/"optimizer_output","separated":root/"separated","reference":root/"reference","project":root/"project_data"}
    for directory in dirs.values(): directory.mkdir(parents=True, exist_ok=True)
    return dirs


def sync_user_file(base: Path, path: Path, *, key: str | None = None):
    backend = get_storage_backend(base)
    return backend.sync_file(current_user_id(), path, key=key)


def sync_user_tree(base: Path, root: Path, *, prefix: str | None = None):
    backend = get_storage_backend(base)
    return backend.sync_tree(current_user_id(), root, prefix=prefix)


def resolve_user_file(base: Path, kind: str, relative_path: str) -> Path | None:
    dirs = user_storage(base); key = {"input":"input","optimizer_output":"output","separated":"separated","reference":"reference","project_data":"project"}.get(kind)
    if not key: return None
    root = dirs[key].resolve(); candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file(): return None
    return candidate
