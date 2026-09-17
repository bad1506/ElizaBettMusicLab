from __future__ import annotations

import base64
import json
import os
import secrets
import urllib.error
import urllib.request
from datetime import datetime, timezone
from calendar import monthrange

import quota


class YooKassaError(RuntimeError):
    pass


def enabled() -> bool:
    return bool(os.getenv("YUKASSA_SHOP_ID", "").strip() and os.getenv("YUKASSA_SECRET_KEY", "").strip())


def prices() -> dict[str, int]:
    return {
        "creator": int(os.getenv("SONA_CREATOR_PRICE_RUB", "990")),
        "pro": int(os.getenv("SONA_PRO_PRICE_RUB", "1990")),
        "studio": int(os.getenv("SONA_STUDIO_PRICE_RUB", "4990")),
    }


def _auth_header() -> str:
    raw = f"{os.environ['YUKASSA_SHOP_ID']}:{os.environ['YUKASSA_SECRET_KEY']}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def _request(method: str, path: str, payload: dict | None = None, idempotence_key: str | None = None) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"https://api.yookassa.ru/v3/{path.lstrip('/')}", data=body, method=method)
    req.add_header("Authorization", _auth_header())
    req.add_header("Content-Type", "application/json")
    if idempotence_key: req.add_header("Idempotence-Key", idempotence_key)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise YooKassaError(f"YooKassa request failed: {exc}") from exc


def create_checkout(user_id: str, plan: str, return_url: str | None = None) -> dict:
    if plan not in prices(): raise YooKassaError("Paid plan is not available")
    if not enabled(): raise YooKassaError("YooKassa is not configured")
    configured_return = (return_url or os.getenv("YUKASSA_RETURN_URL", "")).strip()
    if not configured_return.startswith(("http://", "https://")):
        raise YooKassaError("YUKASSA_RETURN_URL must be an absolute URL")
    amount = prices()[plan]
    payment = _request(
        "POST", "/payments",
        {
            "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": configured_return},
            "description": f"SØNA {quota.PLANS[plan]['name']} — 1 месяц",
            "metadata": {"user_id": user_id, "plan": plan},
        },
        secrets.token_urlsafe(24),
    )
    confirmation = payment.get("confirmation") or {}
    return {"payment_id": payment.get("id"), "status": payment.get("status"), "confirmation_url": confirmation.get("confirmation_url"), "amount_rub": amount}


def verify_payment(payment_id: str) -> dict:
    if not enabled(): raise YooKassaError("YooKassa is not configured")
    return _request("GET", f"/payments/{payment_id}")


def _next_month_iso() -> str:
    now = datetime.now(timezone.utc)
    year = now.year + (1 if now.month == 12 else 0)
    month = 1 if now.month == 12 else now.month + 1
    day = min(now.day, monthrange(year, month)[1])
    return datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc).isoformat()


def handle_webhook(event: dict) -> dict:
    if event.get("event") != "payment.succeeded": return {"ok": True, "handled": False}
    payment = event.get("object") or {}
    payment_id = str(payment.get("id") or "")
    if not payment_id: raise YooKassaError("Webhook payment id is missing")
    verified = verify_payment(payment_id)
    if verified.get("status") != "succeeded" or not verified.get("paid"):
        return {"ok": True, "handled": False, "status": verified.get("status")}
    metadata = verified.get("metadata") or {}
    user_id = str(metadata.get("user_id") or "")
    plan = str(metadata.get("plan") or "")
    if not user_id or plan not in prices(): raise YooKassaError("Payment metadata is invalid")
    state = quota.set_plan(user_id, plan, "active", _next_month_iso())
    return {"ok": True, "handled": True, "payment_id": payment_id, "user_id": user_id, "plan": plan, "usage": state}
