from starlette.requests import Request

import api


def _request(client_host: str = "185.71.76.5", headers: dict[str, str] | None = None) -> Request:
    header_items = []
    for key, value in (headers or {}).items():
        header_items.append((key.lower().encode(), value.encode()))
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/billing/yookassa/webhook",
        "headers": header_items,
        "client": (client_host, 443),
        "server": ("test", 443),
        "scheme": "https",
    }
    return Request(scope)


def test_yookassa_ip_allowlist_is_optional(monkeypatch):
    monkeypatch.delenv("YUKASSA_WEBHOOK_IP_ALLOWLIST", raising=False)
    assert api._yookassa_ip_allowed(_request("203.0.113.10")) is True


def test_yookassa_ip_allowlist_accepts_configured_cidr(monkeypatch):
    monkeypatch.setenv("YUKASSA_WEBHOOK_IP_ALLOWLIST", "185.71.76.0/27,2a02:5180::/32")
    assert api._yookassa_ip_allowed(_request("185.71.76.11")) is True
    assert api._yookassa_ip_allowed(_request("185.71.77.11")) is False


def test_yookassa_ip_allowlist_rejects_invalid_or_unknown_source(monkeypatch):
    monkeypatch.setenv("YUKASSA_WEBHOOK_IP_ALLOWLIST", "185.71.76.0/27")
    assert api._yookassa_ip_allowed(_request("203.0.113.10")) is False


def test_yookassa_ip_allowlist_uses_forwarded_ip_only_when_enabled(monkeypatch):
    monkeypatch.setenv("YUKASSA_WEBHOOK_IP_ALLOWLIST", "185.71.76.0/27")
    request = _request("203.0.113.10", {"X-Forwarded-For": "185.71.76.11, 10.0.0.1"})
    assert api._yookassa_ip_allowed(request) is False
    monkeypatch.setenv("YUKASSA_TRUST_PROXY_HEADERS", "true")
    assert api._yookassa_ip_allowed(request) is True


def test_billing_admin_requires_constant_time_key(monkeypatch):
    monkeypatch.setenv("SONA_BILLING_ADMIN_KEY", "secret-key")
    api._billing_admin_required(_request(headers={"X-Billing-Admin-Key": "secret-key"}))


def test_billing_admin_rejects_missing_or_wrong_key(monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setenv("SONA_BILLING_ADMIN_KEY", "secret-key")
    for supplied in (None, "wrong"):
        headers = {} if supplied is None else {"X-Billing-Admin-Key": supplied}
        try:
            api._billing_admin_required(_request(headers=headers))
        except HTTPException as exc:
            assert exc.status_code == 403
        else:
            raise AssertionError("billing admin authorization unexpectedly succeeded")
