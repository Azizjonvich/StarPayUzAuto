"""ElderPay API client — https://elder.uz/api

Схема работы:
  1. create_order(amount) → ElderPay возвращает order_id
  2. check_order(order_id) → ElderPay возвращает status (paid/pending/cancel)
  3. При status="paid" → начисляем баланс пользователю
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class ElderPayError(Exception):
    def __init__(self, message: str, status: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status = status
        self.payload = payload


class ElderPayAPI:
    """Client for ElderPay payment API."""

    def __init__(
        self,
        shop_id: str,
        shop_key: str,
        api_url: str = "https://elder.uz/api/v1",
    ):
        self.shop_id = shop_id.strip()
        self.shop_key = shop_key.strip()
        self.api_url = api_url.rstrip("/")

    async def _request(
        self, params: dict[str, str | int]
    ) -> dict[str, Any]:
        """Send URL-encoded POST to ElderPay API."""
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                self.api_url,
                data=params,  # aiohttp automatically URL-encodes
            ) as resp:
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    text = await resp.text()
                    logger.error("ElderPay non-JSON response: %s", text[:500])
                    raise ElderPayError(
                        f"Non-JSON response: {text[:200]}",
                        resp.status,
                    )

                logger.info(
                    "ElderPay %s response: status=%s body=%s",
                    params.get("method", "?"),
                    resp.status,
                    str(data)[:300],
                )

                if resp.status >= 400:
                    msg = data.get("message") or data.get("error") or str(data)
                    raise ElderPayError(msg, resp.status, data)

                return data if isinstance(data, dict) else {"data": data}

    async def create_order(self, amount: int) -> dict[str, Any]:
        """Create a payment order.

        Args:
            amount: Amount in UZS (e.g. 50000 for 50,000 so'm)

        Returns:
            {"order": "<order_id>", ...} or {"data": {"order": "<order_id>", ...}}

        Raises:
            ElderPayError on API failure.
        """
        params: dict[str, str | int] = {
            "method": "create",
            "shop_id": self.shop_id,
            "shop_key": self.shop_key,
            "amount": amount,
            "over": 10,
        }
        data = await self._request(params)

        # ElderPay может вернуть как {"order": "..."} так и {"data": {"order": "..."}}
        if "order" in data:
            return data
        if isinstance(data.get("data"), dict) and "order" in data["data"]:
            return data["data"]
        # Fallback — возвращаем как есть
        return data

    async def check_order(self, order_id: str) -> dict[str, Any]:
        """Check payment order status.

        Args:
            order_id: Order ID returned by create_order()

        Returns:
            {"data": {"status": "paid"|"pending"|"cancel"}, ...}

        Raises:
            ElderPayError on API failure.
        """
        params: dict[str, str | int] = {
            "method": "check",
            "order": order_id,
            "shop_id": self.shop_id,
            "shop_key": self.shop_key,
        }
        data = await self._request(params)

        # Нормализуем — извлекаем data.status
        if isinstance(data.get("data"), dict):
            return data
        # Если API вернул status на верхнем уровне
        if "status" in data:
            return {"data": data}
        return data

    @property
    def is_configured(self) -> bool:
        """Check if the client has valid credentials."""
        return bool(self.shop_id and self.shop_key)
