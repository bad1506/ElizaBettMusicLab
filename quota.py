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
    conn.execute("CREATE TABLE IF NOT EXISTS billing_payments (payment_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, plan TEXT NOT NULL, claimed_at TEXT NOT NULL)")
    conn.commit()
    return conn


def _subscription(user_id: str) -> dict:
    if DB_PROVIDER == "ydb":
        row = _ydb().get_subscription(user_id)
        return row or {"plan": "free", "status": "active", "period_end": ""}
    conn = _connect()
    try:
        row = conn.execute("SELECT plan,status,period_end FROM subscriptions WHERE user_id=?", (user_id,)).fetchone()
    finally:
        conn.close()
    return {"plan": str(row[0]), "status": str(row[1]), "period_end": str(row[2] or "")} if row else {"plan": "free", "status": "active", "period_end": ""}


def _plan_for(user_id: str) -> str:
    subscription = _subscription(user_id)
    plan = str(subscription.get("plan") or "free")
    if plan not in PLANS or plan == "free":
        return "free"
    if str(subscription.get("status") or "active").lower() not in {"active", "paid"}:
        return "free"
    period_end = str(subscription.get("period_end") or "").strip()
    if period_end:
        try:
            expiry = datetime.fromisoformat(period_end.replace("Z", "+00:00"))
            if expiry <= datetime.now(timezone.utc):
                return "free"
        except ValueError:
            return "free"
    return plan


def plan_catalog() -> dict[str, dict[str, int | str]]:
    return {key: dict(value) for key, value in PLANS.items()}


def usage(user_id: str) -> dict:
    subscription = _subscription(user_id)
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
    return {"plan": plan, "plan_name": limits["name"], "subscription_status": subscription.get("status", "active") if plan != "free" else "free", "period_end": subscription.get("period_end") or None, "month": month, "period": {"start": _period()[0], "end": _period()[1]}, "features": {feature: {"used": used.get(feature, 0), "limit": int(limits[feature]), "remaining": max(0, int(limits[feature]) - used.get(feature, 0))} for feature in FEATURES}, "storage_mb": int(limits["storage_mb"])}


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


def activate_payment(payment_id: str, user_id: str, plan: str, period_end: str) -> tuple[bool, dict]:
    """Atomically claim a succeeded payment and activate its subscription."""
    if not payment_id or plan not in PLANS or plan == "free":
        raise ValueError("Invalid paid payment activation")
    now = str(int(time.time()))
    if DB_PROVIDER == "ydb":
        claimed = _ydb().activate_billing_payment(payment_id, user_id, plan, period_end, now)
        return bool(claimed), usage(user_id)
    with _LOCK:
        conn = _connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT payment_id FROM billing_payments WHERE payment_id=?", (payment_id,)).fetchone()
            if existing:
                conn.rollback()
                return False, usage(user_id)
            conn.execute("INSERT INTO billing_payments(payment_id,user_id,plan,claimed_at) VALUES(?,?,?,?)", (payment_id,user_id,plan,datetime.now(timezone.utc).isoformat()))
            conn.execute("INSERT INTO subscriptions(user_id,plan,status,period_end,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET plan=excluded.plan,status=excluded.status,period_end=excluded.period_end,updated_at=excluded.updated_at", (user_id,plan,"active",period_end,now))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    return True, usage(user_id)


def claim_payment(payment_id: str, user_id: str, plan: str) -> bool:
    if not payment_id or plan not in PLANS or plan == "free":
        return False
    if DB_PROVIDER == "ydb":
        return bool(_ydb().claim_billing_payment(payment_id, user_id, plan))
    conn = _connect()
    try:
        cursor = conn.execute("INSERT OR IGNORE INTO billing_payments(payment_id,user_id,plan,claimed_at) VALUES(?,?,?,?)", (payment_id,user_id,plan,datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return cursor.rowcount == 1
    finally:
        conn.close()


class QuotaExceeded(Exception):
    def __init__(self, feature: str, item: dict):
        self.feature = feature
        self.item = item
        super().__init__(f"Monthly quota exceeded for {feature}")


def _ydb():
    from ydb_store import get_store
    return get_store()
