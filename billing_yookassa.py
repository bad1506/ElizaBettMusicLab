from __future__ import annotations

import base64
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

import quota

API = "https://api.yookassa.ru/v3"


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


def _auth() -> tuple[str, str]:
    shop = os.getenv("YUKASSA_SHOP_ID", "").strip()
    secret = os.getenv("YUKASSA_SECRET_KEY", "").strip()
    if not shop or not secret:
        raise YooKassaError("Оплата пока не настроена: укажите YUKASSA_SHOP_ID и YUKASSA_SECRET_KEY.")
    return shop, secret


def _headers(*, idempotency_key: str | None = None) -> dict[str, str]:
    shop, secret = _auth()
    token = base64.b64encode(f"{shop}:{secret}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json", "Accept": "application/json"}
    if idempotency_key:
        headers["Idempotence-Key"] = idempotency_key
    return headers


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    try:
        response = httpx.request(method, f"{API}{path}", headers=_headers(**kwargs.pop("_header_args", {})), timeout=20, **kwargs)
    except httpx.HTTPError as exc:
        raise YooKassaError("Платёжный сервис временно недоступен.") from exc
    if response.status_code >= 400:
        try:
            detail = response.json().get("description") or response.json().get("message")
        except Exception:
            detail = None
        raise YooKassaError(str(detail or "Платёжный сервис вернул ошибку."))
    try:
        return response.json()
    except ValueError as exc:
        raise YooKassaError("Платёжный сервис вернул некорректный ответ.") from exc


def create_checkout(user_id: str, plan: str, return_url: str | None = None) -> dict[str, Any]:
    if plan not in prices():
        raise YooKassaError("Неизвестный тариф.")
    url = (return_url or os.getenv("YUKASSA_RETURN_URL", "")).strip()
    if not url:
        raise YooKassaError("Не настроен YUKASSA_RETURN_URL.")
    amount = prices()[plan]
    payload = {
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": url},
        "description": f"SØNA Music Intelligence — {quota.PLANS[plan]['name']} на 1 месяц",
        "metadata": {"user_id": str(user_id), "plan": plan, "service": "sona"},
    }
    payment = _request("POST", "/payments", json=payload, _header_args={"idempotency_key": str(uuid.uuid4())})
    confirmation = payment.get("confirmation") or {}
    confirmation_url = confirmation.get("confirmation_url")
    payment_id = str(payment.get("id") or "").strip()
    if not confirmation_url or not payment_id:
        raise YooKassaError("Не удалось получить корректный платёж от ЮKassa.")
    try:
        quota.record_pending_payment(payment_id, user_id, plan, str(payment.get("status") or "pending"))
    except Exception as exc:
        raise YooKassaError("Платёж создан, но не удалось сохранить его в журнале. Повторите запрос позже.") from exc
    return {"payment_id": payment_id, "status": payment.get("status"), "confirmation_url": confirmation_url, "amount_rub": amount, "plan": plan}


def get_payment(payment_id: str) -> dict[str, Any]:
    if not payment_id or len(payment_id) > 128:
        raise YooKassaError("Некорректный идентификатор платежа.")
    return _request("GET", f"/payments/{payment_id}")


def _activate_from_payment(payment: dict[str, Any]) -> dict[str, Any]:
    if payment.get("status") != "succeeded":
        return {"ok": True, "activated": False, "status": payment.get("status")}

    metadata = payment.get("metadata") or {}
    user_id = str(metadata.get("user_id") or "").strip()
    plan = str(metadata.get("plan") or "").strip()
    payment_id = str(payment.get("id") or "").strip()
    if not user_id or plan not in quota.PLANS or plan == "free" or not payment_id:
        raise YooKassaError("Платёж не содержит корректных данных тарифа.")

    period_end = (datetime.now(timezone.utc) + timedelta(days=31)).isoformat()
    activated, state = quota.activate_payment(payment_id, user_id, plan, period_end)
    if not activated:
        return {"ok": True, "activated": False, "duplicate": True, "payment_id": payment_id, "plan": state.get("plan"), "usage": state}

    return {"ok": True, "activated": True, "user_id": user_id, "payment_id": payment_id, "plan": plan, "usage": state}


def _validate_pending_payment(payment: dict[str, Any], pending: dict[str, Any]) -> None:
    metadata = payment.get("metadata") or {}
    if str(metadata.get("user_id") or "").strip() != str(pending["user_id"]):
        raise YooKassaError("Платёж не совпадает с пользователем из журнала.")
    if str(metadata.get("plan") or "").strip() != str(pending["plan"]):
        raise YooKassaError("Платёж не совпадает с тарифом из журнала.")
    amount = payment.get("amount") or {}
    try:
        actual = Decimal(str(amount.get("value")))
    except (InvalidOperation, TypeError):
        raise YooKassaError("Платёж содержит некорректную сумму.")
    expected = Decimal(str(prices()[pending["plan"]]))
    if amount.get("currency") != "RUB" or actual != expected:
        raise YooKassaError("Сумма или валюта платежа не совпадает с тарифом.")


def reconcile_pending(limit: int = 50) -> dict[str, Any]:
    if not enabled():
        raise YooKassaError("ЮKassa не настроена.")
    pending = quota.pending_payments(limit)
    summary = {"checked": 0, "activated": 0, "duplicates": 0, "canceled": 0, "waiting": 0, "errors": 0, "items": []}
    for row in pending:
        summary["checked"] += 1
        payment_id = row["payment_id"]
        try:
            payment = get_payment(payment_id)
            status = str(payment.get("status") or "pending")
            if status == "succeeded":
                _validate_pending_payment(payment, row)
                result = _activate_from_payment(payment)
                if result.get("duplicate"):
                    summary["duplicates"] += 1
                elif result.get("activated"):
                    summary["activated"] += 1
                summary["items"].append({"payment_id": payment_id, "status": "succeeded", "result": "duplicate" if result.get("duplicate") else "activated"})
            elif status == "canceled":
                quota.mark_pending_payment(payment_id, "canceled")
                summary["canceled"] += 1
                summary["items"].append({"payment_id": payment_id, "status": status})
            else:
                quota.mark_pending_payment(payment_id, status if status in {"pending", "waiting_for_capture"} else "pending")
                summary["waiting"] += 1
                summary["items"].append({"payment_id": payment_id, "status": status})
        except YooKassaError as exc:
            quota.mark_pending_payment(payment_id, "error")
            summary["errors"] += 1
            summary["items"].append({"payment_id": payment_id, "status": "error", "error": str(exc)})
    return summary


def handle_webhook(event: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(event, dict) or event.get("type") != "notification":
        return {"ok": True, "ignored": True}
    if event.get("event") != "payment.succeeded":
        return {"ok": True, "ignored": True, "event": event.get("event")}
    payment_id = str((event.get("object") or {}).get("id") or "").strip()
    if not payment_id:
        raise YooKassaError("Webhook не содержит payment id.")
    return _activate_from_payment(get_payment(payment_id))
