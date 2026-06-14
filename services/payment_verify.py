"""Verify payment webhooks using shop_key."""

import hashlib
import hmac
from typing import Any


def verify_shop_signature(payload: dict[str, Any], shop_key: str) -> bool:
    """
    Verifies HMAC-SHA256 signature from payment webhook.
    """
    sign = payload.get("sign") or payload.get("signature") or payload.get("hash")
    if not sign or not shop_key:
        return False

    data = {k: v for k, v in payload.items() if k not in ("sign", "signature", "hash")}
    check_string = "&".join(f"{k}={data[k]}" for k in sorted(data.keys()))
    # Правильный Python hmac: используем hmac.new()
    expected = hmac.new(
        shop_key.encode(), check_string.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected.lower(), str(sign).lower())


def extract_payment_fields(payload: dict[str, Any]) -> tuple[str | None, int | None, int | None]:
    """
    Извлекает order_id, amount, user_id из webhook payload.
    Поддерживает разные форматы: Fragment API, Click, Payme, Uzum.
    """
    # order_id — пробуем все возможные поля
    order_id = (
        payload.get("order_id")
        or payload.get("shop_order_id")
        or payload.get("merchant_order_id")
        or payload.get("merchant_trans_id")   # Click
        or payload.get("id")
    )

    # amount — поддержка строки "50000.00"
    raw_amount = (
        payload.get("amount")
        or payload.get("sum")
        or payload.get("total")
    )
    try:
        amount_int = int(float(str(raw_amount))) if raw_amount is not None else None
    except (TypeError, ValueError):
        amount_int = None

    # user_id
    raw_user = (
        payload.get("user_id")
        or payload.get("telegram_id")
        or payload.get("customer_id")
        or payload.get("param2")              # некоторые интеграции кладут telegram_id в param2
    )
    try:
        user_int = int(raw_user) if raw_user is not None else None
    except (TypeError, ValueError):
        user_int = None

    return str(order_id) if order_id else None, amount_int, user_int
