import asyncio
import aiohttp
import hashlib
from typing import Optional, Dict, Any
import config


class FragmentAPIClient:
    """Client for fragment-api.uz API v1"""

    def __init__(self):
        raw_key = config.FRAGMENT_API_KEY or ""
        self.api_key = "".join(raw_key.split()) if raw_key else ""
        base = config.FRAGMENT_API_URL.rstrip("/")
        self.api_url = base if base.endswith("/v1") else f"{base}/v1"
        self.shop_id = config.SHOP_ID
        self.shop_key = config.SHOP_KEY

    async def _make_request(
        self, endpoint: str, data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        headers = {
            "X-API-Key": self.api_key.strip(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        timeout = aiohttp.ClientTimeout(total=30)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=data or {}) as response:
                    try:
                        return await response.json(content_type=None)
                    except Exception:
                        text = await response.text()
                        return {"ok": False, "message": text, "status": response.status}
        except aiohttp.ClientConnectorError:
            return {"ok": False, "message": "API serverga ulanib bo'lmadi"}
        except asyncio.TimeoutError:
            return {"ok": False, "message": "API server javob bermadi (timeout)"}
        except Exception as e:
            return {"ok": False, "message": f"So'rov xatoligi: {e}"}

    async def get_stars_price(self, amount: int) -> Dict[str, Any]:
        return await self._make_request("stars/pricing", {"amount": amount})

    async def buy_stars(self, username: str, amount: int) -> Dict[str, Any]:
        return await self._make_request(
            "stars/buy",
            {"username": username.lstrip("@"), "amount": amount},
        )

    async def buy_premium(self, username: str, duration: int) -> Dict[str, Any]:
        return await self._make_request(
            "premium/buy",
            {"username": username.lstrip("@"), "duration": duration},
        )

    async def get_user_info(self, username: str) -> Dict[str, Any]:
        return await self._make_request(
            "getInfo", {"username": username.lstrip("@")}
        )

    async def create_payment(
        self, 
        amount: int, 
        order_id: str, 
        user_id: int,
        description: str = "Hisobni to'ldirish",
        callback_url: str = "",
        redirect_url: str = ""
    ) -> Dict[str, Any]:
        """
        Create payment invoice via Fragment API Uz
        Docs: https://fragment-api.uz/docs/payment
        """
        payload = {
            "shop_id": self.shop_id,
            "amount": amount,
            "order_id": order_id,
            "user_id": user_id,
            "description": description,
            "currency": "UZS",
        }
        # Callback URL для уведомлений об оплате
        if callback_url:
            payload["callback_url"] = callback_url
        # Redirect URL после успешной оплаты
        if redirect_url:
            payload["redirect_url"] = redirect_url
        
        return await self._make_request("payment/create", payload)

    async def check_payment(self, order_id: str) -> Dict[str, Any]:
        """
        Check payment status
        """
        return await self._make_request(
            "payment/status",
            {"shop_id": self.shop_id, "order_id": order_id}
        )

    def verify_callback(self, data: Dict) -> bool:
        received_signature = data.get("signature", "")
        sign_string = f"{data.get('order_id')}:{data.get('amount')}:{self.shop_key}"
        expected_signature = hashlib.sha256(sign_string.encode()).hexdigest()
        return received_signature == expected_signature


api_client = FragmentAPIClient()
