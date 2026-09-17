import billing_yookassa


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
    called = {}

    payment = {"id": "payment-2", "status": "succeeded", "metadata": {"user_id": "user-2", "plan": "creator"}}
    monkeypatch.setattr(billing_yookassa, "get_payment", lambda payment_id: called.setdefault("id", payment_id) or payment)
    monkeypatch.setattr(billing_yookassa.quota, "set_plan", lambda user_id, plan, status, period_end: {"plan": plan, "status": status, "period_end": period_end})
    result = billing_yookassa.handle_webhook({"type": "notification", "event": "payment.succeeded", "object": {"id": "payment-2"}})
    assert called["id"] == "payment-2"
    assert result["activated"] is True
    assert result["plan"] == "creator"
