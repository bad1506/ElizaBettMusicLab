import tempfile
from pathlib import Path

import quota


def test_free_quota_is_persistent():
    with tempfile.TemporaryDirectory() as tmp:
        old_path = quota.SQLITE_PATH
        quota.SQLITE_PATH = Path(tmp) / "quota.sqlite3"
        try:
            user = "test-user"
            state = quota.usage(user)
            assert state["plan"] == "free"
            assert state["features"]["chat"]["remaining"] == 30
            quota.consume(user, "chat")
            assert quota.usage(user)["features"]["chat"]["used"] == 1
        finally:
            quota.SQLITE_PATH = old_path


def test_quota_rejects_when_limit_reached():
    with tempfile.TemporaryDirectory() as tmp:
        old_path = quota.SQLITE_PATH
        quota.SQLITE_PATH = Path(tmp) / "quota.sqlite3"
        try:
            user = "limited-user"
            for _ in range(30):
                quota.consume(user, "chat")
            try:
                quota.consume(user, "chat")
                assert False, "expected QuotaExceeded"
            except quota.QuotaExceeded as exc:
                assert exc.feature == "chat"
        finally:
            quota.SQLITE_PATH = old_path

# CI trigger: validate the current production billing/quota HEAD.
