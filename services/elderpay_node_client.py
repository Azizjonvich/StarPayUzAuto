"""
ElderPay Node.js API Client
Connects Python bot to Node.js ElderPay API
"""

import logging
from typing import Any
import aiohttp

logger = logging.getLogger(__name__)


class ElderPayNodeClient:
    """Client for Node.js ElderPay API"""

    def __init__(self, api_url: str):
        """
        Initialize client
        
        Args:
            api_url: Base URL of Node.js API (e.g. https://web-production-3d7ba.up.railway.app)
        """
        self.api_url = api_url.rstrip("/")
        self.base_url = f"{self.api_url}/api/elderpay"

    async def create_order(
        self,
        amount: int,
        user_id: int,
        local_order_id: str
    ) -> dict[str, Any]:
        """
        Create payment order via Node.js API
        
        Args:
            amount: Amount in UZS
            user_id: Telegram user ID
            local_order_id: Local order ID from bot database
            
        Returns:
            {
                "ok": true,
                "order_id": "EP123456789",
                "card_number": "9860180101712578",
                "amount": 10000,
                "status": "pending"
            }
        """
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.base_url}/create",
                    json={
                        "amount": amount,
                        "user_id": str(user_id),
                        "local_order_id": local_order_id
                    }
                ) as resp:
                    data = await resp.json()
                    
                    logger.info(
                        "ElderPay Node create: status=%s order_id=%s",
                        resp.status, data.get("order_id")
                    )
                    
                    if resp.status >= 400 or not data.get("ok"):
                        error_msg = data.get("error", "Unknown error")
                        logger.error("ElderPay Node create failed: %s", error_msg)
                        raise Exception(error_msg)
                    
                    return data
                    
        except aiohttp.ClientError as e:
            logger.error("ElderPay Node API connection error: %s", e)
            raise Exception(f"Cannot connect to ElderPay API: {e}")

    async def check_order(self, order_id: str) -> dict[str, Any]:
        """
        Check order status via Node.js API
        
        Args:
            order_id: ElderPay order ID (returned by create_order)
            
        Returns:
            {
                "ok": true,
                "order_id": "EP123456789",
                "status": "paid" | "pending" | "cancel"
            }
        """
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.base_url}/check/{order_id}"
                ) as resp:
                    data = await resp.json()
                    
                    logger.info(
                        "ElderPay Node check: order=%s status=%s",
                        order_id, data.get("status")
                    )
                    
                    if resp.status >= 400 or not data.get("ok"):
                        error_msg = data.get("error", "Unknown error")
                        logger.error("ElderPay Node check failed: %s", error_msg)
                        raise Exception(error_msg)
                    
                    return data
                    
        except aiohttp.ClientError as e:
            logger.error("ElderPay Node API connection error: %s", e)
            raise Exception(f"Cannot connect to ElderPay API: {e}")

    async def get_pending_orders(self) -> dict[str, Any]:
        """
        Get all pending orders
        
        Returns:
            {
                "ok": true,
                "count": 5,
                "orders": [...]
            }
        """
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.base_url}/pending"
                ) as resp:
                    data = await resp.json()
                    
                    if resp.status >= 400 or not data.get("ok"):
                        error_msg = data.get("error", "Unknown error")
                        logger.error("ElderPay Node pending failed: %s", error_msg)
                        raise Exception(error_msg)
                    
                    return data
                    
        except aiohttp.ClientError as e:
            logger.error("ElderPay Node API connection error: %s", e)
            raise Exception(f"Cannot connect to ElderPay API: {e}")

    @property
    def is_configured(self) -> bool:
        """Check if client is configured"""
        return bool(self.api_url)
