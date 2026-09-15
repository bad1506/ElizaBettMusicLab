from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("WEB_AUTH_DB", Path(__file__).resolve().parent / "web_auth.sqlite3"))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at INTEGER NOT NULL)")
    conn.commit()
    return conn


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


def register(name: str, email: str, password: str) -> dict:
    now = str(int(__import__("time").time()))
    user_id = secrets.token_hex(16)
    conn = _connect()
    try:
        conn.execute("INSERT INTO users(id,name,email,password_hash,created_at) VALUES(?,?,?,?,?)", (user_id, name.strip(), email.lower().strip(), _hash_password(password), now))
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Email уже зарегистрирован")
    finally:
        conn.close()
    return create_session(user_id)


def login(email: str, password: str) -> dict:
    conn = _connect()
    try:
        row = conn.execute("SELECT id,name,email,password_hash FROM users WHERE email=?", (email.lower().strip(),)).fetchone()
    finally:
        conn.close()
    if not row or not _verify_password(password, row["password_hash"]):
        raise ValueError("Неверный email или пароль")
    return create_session(row["id"])


def create_session(user_id: str) -> dict:
    import time
    token = secrets.token_urlsafe(48)
    expires = int(time.time()) + 60 * 60 * 24 * 30
    conn = _connect()
    try:
        conn.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user_id, expires))
        conn.commit()
        row = conn.execute("SELECT id,name,email,created_at FROM users WHERE id=?", (user_id,)).fetchone()
    finally:
        conn.close()
    return {"token": token, "expires_at": expires, "user": dict(row)}


def get_user(token: str) -> dict | None:
    import time
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = _connect()
    try:
        row = conn.execute("SELECT u.id,u.name,u.email,u.created_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?", (token_hash, int(time.time()))).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None
