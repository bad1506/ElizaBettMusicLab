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

    def fake_get_payment(payment_id):
        called["id"] = payment_id
        return payment

    monkeypatch.setattr(billing_yookassa, "get_payment", fake_get_payment)
    monkeypatch.setattr(billing_yookassa.quota, "claim_payment", lambda payment_id, user_id, plan: True)
    monkeypatch.setattr(billing_yookassa.quota, "set_plan", lambda user_id, plan, status, period_end: {"plan": plan, "status": status, "period_end": period_end})
    result = billing_yookassa.handle_webhook({"type": "notification", "event": "payment.succeeded", "object": {"id": "payment-2"}})
    assert called["id"] == "payment-2"
    assert result["activated"] is True
    assert result["plan"] == "creator"


def test_webhook_retry_can_activate_after_transient_set_plan_failure(monkeypatch):
    monkeypatch.setenv("YUKASSA_SHOP_ID", "shop")
    monkeypatch.setenv("YUKASSA_SECRET_KEY", "secret")

    payment = {"id": "payment-retry", "status": "succeeded", "metadata": {"user_id": "user-retry", "plan": "pro"}}
    monkeypatch.setattr(billing_yookassa, "get_payment", lambda payment_id: payment)

    calls = {"set_plan": 0, "claim": 0}

    def flaky_set_plan(user_id, plan, status, period_end):
        calls["set_plan"] += 1
        if calls["set_plan"] == 1:
            raise RuntimeError("temporary database failure")
        return {"plan": plan, "status": status, "period_end": period_end}

    def claim(payment_id, user_id, plan):
        calls["claim"] += 1
        return True

    monkeypatch.setattr(billing_yookassa.quota, "set_plan", flaky_set_plan)
    monkeypatch.setattr(billing_yookassa.quota, "claim_payment", claim)

    try:
        billing_yookassa.handle_webhook({"type": "notification", "event": "payment.succeeded", "object": {"id": "payment-retry"}})
    except RuntimeError:
        pass
    else:
        raise AssertionError("first activation attempt must fail")

    result = billing_yookassa.handle_webhook({"type": "notification", "event": "payment.succeeded", "object": {"id": "payment-retry"}})
    assert result["activated"] is True
    assert result["plan"] == "pro"
    assert calls["set_plan"] == 2
    assert calls["claim"] == 1
