import concurrent.futures
import sqlite3

import billing_yookassa
import quota


def test_billing_disabled_without_credentials(monkeypatch):
    monkeypatch.delenv("YUKASSA_SHOP_ID", raising=False)
    monkeypatch.delenv("YUKASSA_SECRET_KEY", raising=False)
    assert billing_yookassa.enabled() is False


def test_create_checkout_uses_idempotency_and_metadata(monkeypatch):
    monkeypatch.setenv("YUKASSA_SHOP_ID", "shop")
    monkeypatch.setenv("YUKASSA_SECRET_KEY", "secret")
    monkeypatch.setenv("YUKASSA_RETURN_URL", "https://example.test/paid")
    captured = {}

    def fake_request(method, path, **kwargs):
        captured.update(method=method, path=path, kwargs=kwargs)
        return {"id": "payment-1", "status": "pending", "confirmation": {"confirmation_url": "https://yookassa.test/pay"}}

    monkeypatch.setattr(billing_yookassa, "_request", fake_request)
    result = billing_yookassa.create_checkout("user-1", "pro")
    payload = captured["kwargs"]["json"]
    assert result["payment_id"] == "payment-1"
    assert payload["metadata"] == {"user_id": "user-1", "plan": "pro", "service": "sona"}
    assert captured["kwargs"]["_header_args"]["idempotency_key"]


def test_webhook_reverifies_successful_payment(monkeypatch):
    monkeypatch.setenv("YUKASSA_SHOP_ID", "shop")
    monkeypatch.setenv("YUKASSA_SECRET_KEY", "secret")

    payment = {"id": "payment-2", "status": "succeeded", "metadata": {"user_id": "user-2", "plan": "creator"}}
    called = {}

    def fake_get_payment(payment_id):
        called["id"] = payment_id
        return payment

    monkeypatch.setattr(billing_yookassa, "get_payment", fake_get_payment)
    monkeypatch.setattr(billing_yookassa.quota, "activate_payment", lambda payment_id, user_id, plan, period_end: (True, {"plan": plan, "status": "active", "period_end": period_end}))
    result = billing_yookassa.handle_webhook({"type": "notification", "event": "payment.succeeded", "object": {"id": "payment-2"}})
    assert called["id"] == "payment-2"
    assert result["activated"] is True
    assert result["plan"] == "creator"


def _use_temp_sqlite(monkeypatch, tmp_path):
    monkeypatch.setattr(quota, "DB_PROVIDER", "sqlite")
    monkeypatch.setattr(quota, "SQLITE_PATH", tmp_path / "billing.sqlite3")


def test_duplicate_webhook_does_not_refresh_subscription(monkeypatch, tmp_path):
    _use_temp_sqlite(monkeypatch, tmp_path)
    payment = {"id": "payment-duplicate", "status": "succeeded", "metadata": {"user_id": "user-duplicate", "plan": "pro"}}
    monkeypatch.setattr(billing_yookassa, "get_payment", lambda payment_id: payment)

    first = billing_yookassa.handle_webhook({"type": "notification", "event": "payment.succeeded", "object": {"id": payment["id"]}})
    conn = sqlite3.connect(quota.SQLITE_PATH)
    try:
        before = conn.execute("SELECT period_end,updated_at FROM subscriptions WHERE user_id=?", ("user-duplicate",)).fetchone()
    finally:
        conn.close()

    duplicate = billing_yookassa.handle_webhook({"type": "notification", "event": "payment.succeeded", "object": {"id": payment["id"]}})
    conn = sqlite3.connect(quota.SQLITE_PATH)
    try:
        after = conn.execute("SELECT period_end,updated_at FROM subscriptions WHERE user_id=?", ("user-duplicate",)).fetchone()
    finally:
        conn.close()

    assert first["activated"] is True
    assert duplicate["activated"] is False
    assert duplicate["duplicate"] is True
    assert after == before
    assert duplicate["usage"]["period_end"] == first["usage"]["period_end"]


def test_concurrent_duplicate_webhooks_only_activate_once(monkeypatch, tmp_path):
    _use_temp_sqlite(monkeypatch, tmp_path)
    payment = {"id": "payment-concurrent", "status": "succeeded", "metadata": {"user_id": "user-concurrent", "plan": "creator"}}
    monkeypatch.setattr(billing_yookassa, "get_payment", lambda payment_id: payment)

    event = {"type": "notification", "event": "payment.succeeded", "object": {"id": payment["id"]}}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: billing_yookassa.handle_webhook(event), range(8)))

    activated = [result for result in results if result.get("activated")]
    duplicates = [result for result in results if result.get("duplicate")]
    assert len(activated) == 1
    assert len(duplicates) == 7

    conn = sqlite3.connect(quota.SQLITE_PATH)
    try:
        payment_count = conn.execute("SELECT COUNT(*) FROM billing_payments WHERE payment_id=?", (payment["id"],)).fetchone()[0]
        subscription_count = conn.execute("SELECT COUNT(*) FROM subscriptions WHERE user_id=?", ("user-concurrent",)).fetchone()[0]
    finally:
        conn.close()
    assert payment_count == 1
    assert subscription_count == 1
