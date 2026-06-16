"""
HTTP client for Node.js Payment Server (elderpay-api).

The bot communicates with the separate Node.js payment service
to confirm payments, check status, and list pending orders.

All requests go to: PAYMENT_SERVER_URL (env var or https://payment-server.railway.app)
"""
import json
import logging
import os

import aiohttp

logger = logging.getLogger(__name__)

# Payment server URL (separate Railway service)
PAYMENT_SERVER_URL = os.environ.get(
    "PAYMENT_SERVER_URL",
    "",  # Must be set in production: https://your-service.railway.app
).rstrip("/")

# Admin secret for confirming payments
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "")


async def _request(method: str, path: str, data: dict | None = None) -> dict:
    """Make HTTP request to payment server."""
    if not PAYMENT_SERVER_URL:
        return {"ok": False, "error": "PAYMENT_SERVER_URL not configured"}

    url = f"{PAYMENT_SERVER_URL}{path}"
    timeout = aiohttp.ClientTimeout(total=15)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            if method == "GET":
                async with session.get(url) as resp:
                    return await resp.json()
            else:
                async with session.post(url, json=data) as resp:
                    return await resp.json()
    except Exception as e:
        logger.error("Payment server request failed: %s", e)
        return {"ok": False, "error": str(e)}


async def confirm_payment(order_id: str) -> dict:
    """
    Confirm a payment. Credits user balance + sends Telegram notification.
    
    Args:
        order_id: Local order ID (e.g. "topup_abc123")
    
    Returns:
        {"ok": true, "message": "...", "amount": 50000, "new_balance": 150000}
    """
    return await _request("POST", "/api/payment/confirm", {
        "order_id": order_id,
        "admin_secret": ADMIN_SECRET,
    })


async def check_payment(order_id: str) -> dict:
    """
    Check if payment was processed.
    
    Args:
        order_id: Local order ID
    
    Returns:
        {"ok": true, "paid": true/false, "amount": 50000}
    """
    return await _request("POST", "/api/payment/check", {
        "order_id": order_id,
    })


async def get_pending_orders() -> list[dict]:
    """
    Get list of pending topup orders.
    
    Returns:
        {"ok": true, "count": 5, "orders": [...]}
    """
    result = await _request("GET", "/api/payment/pending")
    return result.get("orders", []) if result.get("ok") else []
