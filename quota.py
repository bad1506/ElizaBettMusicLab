from __future__ import annotations

import os
import sqlite3
import time
from calendar import monthrange
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

PLANS: dict[str, dict[str, int | str]] = {
    "free": {"name": "Free", "chat": 30, "songwriter": 10, "analysis": 5, "mastering": 2, "trends": 5, "production": 1, "stems": 1, "storage_mb": 500},
    "creator": {"name": "Creator", "chat": 300, "songwriter": 100, "analysis": 50, "mastering": 20, "trends": 30, "production": 10, "stems": 10, "storage_mb": 5000},
    "pro": {"name": "Pro", "chat": 1500, "songwriter": 500, "analysis": 200, "mastering": 80, "trends": 100, "production": 40, "stems": 30, "storage_mb": 25000},
    "studio": {"name": "Studio", "chat": 5000, "songwriter": 2000, "analysis": 1000, "mastering": 300, "trends": 300, "production": 150, "stems": 100, "storage_mb": 100000},
}
FEATURES = ("chat", "songwriter", "analysis", "mastering", "trends", "production", "stems")
DB_PROVIDER = os.getenv("SONA_DB_PROVIDER", "sqlite").strip().lower()
DATA_DIR = Path(os.getenv("SONA_DATA_DIR", "/var/data/sona"))
SQLITE_PATH = Path(os.getenv("WEB_AUTH_DB", DATA_DIR / "web_auth.sqlite3"))
_LOCK = Lock()


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _period() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    days = monthrange(now.year, now.month)[1]
    return f"{now.year:04d}-{now.month:02d}-01T00:00:00Z", f"{now.year:04d}-{now.month:02d}-{days:02d}T23:59:59Z"


def _connect() -> sqlite3.Connection:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE IF NOT EXISTS subscriptions (user_id TEXT PRIMARY KEY, plan TEXT NOT NULL, status TEXT NOT NULL, period_end TEXT, updated_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS usage_monthly (user_id TEXT NOT NULL, month TEXT NOT NULL, feature TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(user_id, month, feature))")
    conn.commit()
    return conn


def _ydb():
    from ydb_store import get_store
    return get_store()


def _plan_for(user_id: str) -> str:
    if DB_PROVIDER == "ydb":
        row = _ydb().get_subscription(user_id)
        return str(row.get("plan") or "free") if row else "free"
    conn = _connect()
    try:
        row = conn.execute("SELECT plan FROM subscriptions WHERE user_id=?", (user_id,)).fetchone()
    finally:
        conn.close()
    return str(row[0]) if row and row[0] in PLANS else "free"


def plan_catalog() -> dict[str, dict[str, int | str]]:
    return {key: dict(value) for key, value in PLANS.items()}


def usage(user_id: str) -> dict:
    plan = _plan_for(user_id)
    limits = PLANS[plan]
    month = _month_key()
    if DB_PROVIDER == "ydb":
        rows = _ydb().get_usage(user_id, month)
        used = {str(row["feature"]): int(row["used"]) for row in rows}
    else:
        conn = _connect()
        try:
            rows = conn.execute("SELECT feature,used FROM usage_monthly WHERE user_id=? AND month=?", (user_id, month)).fetchall()
        finally:
            conn.close()
        used = {str(row["feature"]): int(row["used"]) for row in rows}
    return {
        "plan": plan,
        "plan_name": limits["name"],
        "month": month,
        "period": {"start": _period()[0], "end": _period()[1]},
        "features": {feature: {"used": used.get(feature, 0), "limit": int(limits[feature]), "remaining": max(0, int(limits[feature]) - used.get(feature, 0))} for feature in FEATURES},
        "storage_mb": int(limits["storage_mb"]),
    }


def check(user_id: str, feature: str, units: int = 1) -> tuple[bool, dict]:
    if feature not in FEATURES:
        raise ValueError(f"Unknown quota feature: {feature}")
    if units < 1:
        raise ValueError("units must be positive")
    state = usage(user_id)
    return state["features"][feature]["remaining"] >= units, state


def consume(user_id: str, feature: str, units: int = 1) -> dict:
    if feature not in FEATURES:
        raise ValueError(f"Unknown quota feature: {feature}")
    if units < 1:
        raise ValueError("units must be positive")
    plan = _plan_for(user_id)
    limit = int(PLANS[plan][feature])
    month = _month_key()
    if DB_PROVIDER == "ydb":
        ok, _ = _ydb().consume_usage(user_id, month, feature, units, limit)
        if not ok:
            state = usage(user_id)
            raise QuotaExceeded(feature, state["features"][feature])
        return usage(user_id)
    with _LOCK:
        conn = _connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT used FROM usage_monthly WHERE user_id=? AND month=? AND feature=?", (user_id, month, feature)).fetchone()
            used = int(row[0]) if row else 0
            if used + units > limit:
                conn.rollback()
                state = usage(user_id)
                raise QuotaExceeded(feature, state["features"][feature])
            conn.execute("INSERT INTO usage_monthly(user_id,month,feature,used) VALUES(?,?,?,?) ON CONFLICT(user_id,month,feature) DO UPDATE SET used=excluded.used", (user_id, month, feature, used + units))
            conn.commit()
        finally:
            conn.close()
    return usage(user_id)


def set_plan(user_id: str, plan: str, status: str = "active", period_end: str | None = None) -> dict:
    if plan not in PLANS:
        raise ValueError(f"Unknown plan: {plan}")
    now = str(int(time.time()))
    if DB_PROVIDER == "ydb":
        _ydb().set_subscription(user_id, plan, status, period_end or "", now)
    else:
        conn = _connect()
        try:
            conn.execute("INSERT INTO subscriptions(user_id,plan,status,period_end,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET plan=excluded.plan,status=excluded.status,period_end=excluded.period_end,updated_at=excluded.updated_at", (user_id, plan, status, period_end, now))
            conn.commit()
        finally:
            conn.close()
    return usage(user_id)


class QuotaExceeded(Exception):
    def __init__(self, feature: str, item: dict):
        self.feature = feature
        self.item = item
        super().__init__(f"Monthly quota exceeded for {feature}")
