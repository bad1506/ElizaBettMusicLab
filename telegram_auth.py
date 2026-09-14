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
    """Validate Telegram Mini App initData using the bot token.

    Telegram signs the sorted query-string fields with a key derived from the
    bot token and the constant `WebAppData`. The raw initData must never be
    trusted on the client; this function is intended for the backend.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise TelegramAuthError("TELEGRAM_BOT_TOKEN не настроен")
    if not init_data:
        raise TelegramAuthError("Telegram initData отсутствует")

    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = fields.pop("hash", "")
    if not received_hash:
        raise TelegramAuthError("Telegram hash отсутствует")

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(fields.items())
    )
    secret_key = hmac.new(
        b"WebAppData", token.encode("utf-8"), hashlib.sha256
    ).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise TelegramAuthError("Недействительная подпись Telegram")

    try:
        auth_date = int(fields.get("auth_date", "0"))
    except ValueError as exc:
        raise TelegramAuthError("Некорректный auth_date") from exc

    if auth_date <= 0 or time.time() - auth_date > max_age:
        raise TelegramAuthError("Telegram initData устарел")

    user: dict[str, Any] = {}
    if fields.get("user"):
        try:
            user = json.loads(fields["user"])
        except json.JSONDecodeError as exc:
            raise TelegramAuthError("Некорректные данные пользователя Telegram") from exc

    return {
        "user": user,
        "auth_date": auth_date,
        "query_id": fields.get("query_id"),
        "start_param": fields.get("start_param"),
    }
