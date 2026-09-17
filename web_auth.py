from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from pathlib import Path

DB_PROVIDER = os.getenv("SONA_DB_PROVIDER", "sqlite").strip().lower()

DATA_DIR = Path(os.getenv("SONA_DATA_DIR", "/var/data/sona"))
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    DATA_DIR = Path(__file__).resolve().parent / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("WEB_AUTH_DB", DATA_DIR / "web_auth.sqlite3"))


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return f"pbkdf2_sha256$240000${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt_hex, digest_hex = stored.split("$", 3)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _ydb():
    from ydb_store import get_store
    return get_store()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at INTEGER NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL)")
    conn.commit()
    return conn


def register(name: str, email: str, password: str) -> dict:
    if DB_PROVIDER == "ydb":
        result = _ydb().register(name, email, _hash_password(password))
        user = result["user"]
        session = create_session(user["id"])
        add_activity(user["id"], "account", "Аккаунт создан", "Добро пожаловать в SØNA")
        return session

    now = str(int(time.time()))
    user_id = secrets.token_hex(16)
    conn = _connect()
    try:
        conn.execute("INSERT INTO users(id,name,email,password_hash,created_at) VALUES(?,?,?,?,?)", (user_id, name.strip(), email.lower().strip(), _hash_password(password), now))
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Email уже зарегистрирован")
    finally:
        conn.close()
    result = create_session(user_id)
    add_activity(user_id, "account", "Аккаунт создан", "Добро пожаловать в SØNA")
    return result


def login(email: str, password: str) -> dict:
    if DB_PROVIDER == "ydb":
        row = _ydb().get_user_by_email(email)
        if not row or not _verify_password(password, row["password_hash"]):
            raise ValueError("Неверный email или пароль")
        result = create_session(row["id"])
        add_activity(row["id"], "account", "Вход в SØNA", "Успешная авторизация")
        return result

    conn = _connect()
    try:
        row = conn.execute("SELECT id,name,email,password_hash FROM users WHERE email=?", (email.lower().strip(),)).fetchone()
    finally:
        conn.close()
    if not row or not _verify_password(password, row["password_hash"]):
        raise ValueError("Неверный email или пароль")
    result = create_session(row["id"])
    add_activity(row["id"], "account", "Вход в SØNA", "Успешная авторизация")
    return result


def create_session(user_id: str) -> dict:
    token = secrets.token_urlsafe(48)
    expires = int(time.time()) + 60 * 60 * 24 * 30
    if DB_PROVIDER == "ydb":
        _ydb().create_session(user_id, token, expires)
        user = _ydb().get_user_by_id(user_id)
        if not user:
            raise ValueError("Пользователь не найден")
        return {"token": token, "expires_at": expires, "user": user}

    conn = _connect()
    try:
        conn.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user_id, expires))
        conn.commit()
        row = conn.execute("SELECT id,name,email,created_at FROM users WHERE id=?", (user_id,)).fetchone()
    finally:
        conn.close()
    return {"token": token, "expires_at": expires, "user": dict(row)}


def get_user(token: str) -> dict | None:
    if not token:
        return None
    if DB_PROVIDER == "ydb":
        return _ydb().get_user_by_token(token)

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = _connect()
    try:
        row = conn.execute("SELECT u.id,u.name,u.email,u.created_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?", (token_hash, int(time.time()))).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def add_activity(user_id: str, kind: str, title: str, detail: str = "") -> None:
    if DB_PROVIDER == "ydb":
        _ydb().add_activity(user_id, kind, title, detail)
        return

    conn = _connect()
    try:
        conn.execute("INSERT INTO activity(user_id,kind,title,detail,created_at) VALUES(?,?,?,?,?)", (user_id, kind[:40], title[:160], detail[:1000], str(int(time.time()))))
        conn.commit()
    finally:
        conn.close()


def get_activity(user_id: str, limit: int = 50) -> list[dict]:
    if DB_PROVIDER == "ydb":
        return _ydb().get_activity(user_id, limit)

    conn = _connect()
    try:
        rows = conn.execute("SELECT id,kind,title,detail,created_at FROM activity WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, max(1, min(limit, 100)))).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]
