from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl
from typing import Any


class TelegramAuthError(ValueError):
    pass


def validate_init_data(init_data: str, max_age: int = 86400) -> dict[str, Any]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise TelegramAuthError("Telegram auth is not configured")
    if not init_data:
        raise TelegramAuthError("Telegram initData is missing")
    if len(init_data) > 8192:
        raise TelegramAuthError("Telegram initData is too large")

    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = fields.pop("hash", "")
    if not received_hash:
        raise TelegramAuthError("Telegram hash is missing")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise TelegramAuthError("Invalid Telegram signature")

    try:
        auth_date = int(fields.get("auth_date", "0"))
    except ValueError as exc:
        raise TelegramAuthError("Invalid auth_date") from exc

    now = int(time.time())
    if auth_date <= 0 or auth_date > now + 60 or now - auth_date > max_age:
        raise TelegramAuthError("Telegram initData is expired or from the future")

    user: dict[str, Any] = {}
    if fields.get("user"):
        try:
            user = json.loads(fields["user"])
        except json.JSONDecodeError as exc:
            raise TelegramAuthError("Invalid Telegram user data") from exc

    # Protected API access must always map to a real Telegram user.
    # A signed initData payload without user.id must never fall back to shared
    # local storage or the synthetic "local" identity.
    if not user or not user.get("id"):
        raise TelegramAuthError("Telegram user id is missing")

    return {
        "user": user,
        "auth_date": auth_date,
        "query_id": fields.get("query_id"),
        "start_param": fields.get("start_param"),
    }
