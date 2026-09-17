from datetime import datetime, timedelta, timezone

import billing_activation
import quota


def _sqlite(monkeypatch, tmp_path):
    monkeypatch.setattr(quota, "DB_PROVIDER", "sqlite")
    monkeypatch.setattr(quota, "SQLITE_PATH", tmp_path / "billing.sqlite3")


def _period(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_active_subscription_is_extended_from_existing_end(monkeypatch, tmp_path):
    _sqlite(monkeypatch, tmp_path)
    existing_end = (datetime.now(timezone.utc) + timedelta(days=12)).isoformat()
    quota.set_plan("user-1", "creator", "active", existing_end)

    activated, state = billing_activation.activate_payment("payment-1", "user-1", "pro")

    assert activated is True
    actual = _period(state["period_end"])
    assert actual >= _period(existing_end) + timedelta(days=30, hours=23)
    assert state["plan"] == "pro"


def test_expired_subscription_starts_from_now(monkeypatch, tmp_path):
    _sqlite(monkeypatch, tmp_path)
    expired = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    quota.set_plan("user-2", "creator", "active", expired)

    before = datetime.now(timezone.utc)
    activated, state = billing_activation.activate_payment("payment-2", "user-2", "creator")
    after = datetime.now(timezone.utc)

    assert activated is True
    actual = _period(state["period_end"])
    assert before + timedelta(days=31) <= actual <= after + timedelta(days=31, seconds=1)


def test_duplicate_payment_does_not_extend_twice(monkeypatch, tmp_path):
    _sqlite(monkeypatch, tmp_path)
    first, state1 = billing_activation.activate_payment("payment-3", "user-3", "pro")
    second, state2 = billing_activation.activate_payment("payment-3", "user-3", "pro")

    assert first is True
    assert second is False
    assert state2["period_end"] == state1["period_end"]


def test_two_different_payments_extend_cumulatively(monkeypatch, tmp_path):
    _sqlite(monkeypatch, tmp_path)
    first, state1 = billing_activation.activate_payment("payment-4a", "user-4", "creator")
    second, state2 = billing_activation.activate_payment("payment-4b", "user-4", "creator")

    assert first is True
    assert second is True
    assert _period(state2["period_end"]) >= _period(state1["period_end"]) + timedelta(days=30, hours=23)


def test_repeated_payments_can_change_plan_while_extending(monkeypatch, tmp_path):
    _sqlite(monkeypatch, tmp_path)
    _, state1 = billing_activation.activate_payment("payment-5a", "user-5", "creator")
    _, state2 = billing_activation.activate_payment("payment-5b", "user-5", "studio")

    assert state2["plan"] == "studio"
    assert _period(state2["period_end"]) >= _period(state1["period_end"]) + timedelta(days=30, hours=23)
