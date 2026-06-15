"""Client for Fragment API Uz — https://fragment-api.uz/"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)


class FragmentAPIError(Exception):
    def __init__(self, message: str, status: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status = status
        self.payload = payload


class FragmentAPI:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        # Strip all whitespace including newlines, carriage returns
        raw_key = api_key or settings.fragment_api_key or ""
        self.api_key = "".join(raw_key.split())  # Remove ALL whitespace
        self.base_url = (base_url or settings.fragment_api_base).rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(
                method, url, headers=self._headers(), json=json
            ) as resp:
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    data = {"raw": await resp.text()}

                if resp.status >= 400:
                    msg = data.get("message") or data.get("error") or str(data)
                    raise FragmentAPIError(msg, resp.status, data)
                if isinstance(data, dict):
                    return data
                return {"data": data}

    async def get_balance(self) -> dict[str, Any]:
        """Project wallet balance on Fragment platform."""
        for path in ("wallet/balance", "balance", "account/balance"):
            try:
                return await self._request("GET", path)
            except FragmentAPIError as e:
                if e.status == 404:
                    continue
                raise
        return {"balance": None, "note": "Adjust FRAGMENT_API_BASE per docs"}

    async def get_stars_price(self, quantity: int) -> dict[str, Any]:
        for path in ("stars/price", "prices/stars"):
            try:
                return await self._request(
                    "POST", path, json={"quantity": quantity}
                )
            except FragmentAPIError:
                try:
                    return await self._request(
                        "GET", f"{path}?quantity={quantity}"
                    )
                except FragmentAPIError:
                    continue
        return {"quantity": quantity, "price": None}

    async def buy_stars(self, username: str, quantity: int) -> dict[str, Any]:
        username = username.lstrip("@")
        return await self._request(
            "POST",
            "stars/buy",
            json={"username": username, "amount": quantity},
        )

    async def buy_premium(self, username: str, months: int) -> dict[str, Any]:
        username = username.lstrip("@")
        return await self._request(
            "POST",
            "premium/buy",
            json={"username": username, "duration": months},
        )

    async def buy_gift(self, username: str, gift_id: str) -> dict[str, Any]:
        """
        DEPRECATED: Fragment API не поддерживает отправку подарков.
        Используйте services.telethon_client.gift_sender вместо этого.
        """
        return {
            "ok": False,
            "error": "Gift sending not supported by Fragment API. Use Telethon instead."
        }

    async def buy_phone(self, username: str, country: str) -> dict[str, Any]:
        username = username.lstrip("@")
        for path in ("phone/buy", "orders/phone", "number/order"):
            try:
                return await self._request(
                    "POST",
                    path,
                    json={"username": username, "country": country},
                )
            except FragmentAPIError as e:
                if e.status == 404:
                    continue
                raise
        raise FragmentAPIError("Phone endpoint not found — check API docs")


fragment_client = FragmentAPI()
