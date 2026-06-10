"""Click payment integration for automatic balance top-up"""
import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


def verify_click_signature(
    click_trans_id: str,
    service_id: str,
    secret_key: str,
    merchant_trans_id: str,
    amount: str,
    action: str,
    sign_time: str,
    received_sign: str
) -> bool:
    """Verify Click webhook signature"""
    sign_string = f"{click_trans_id}{service_id}{secret_key}{merchant_trans_id}{amount}{action}{sign_time}"
    expected_sign = hashlib.md5(sign_string.encode()).hexdigest()
    return expected_sign == received_sign


async def handle_click_prepare(payload: dict, service_id: str, secret_key: str) -> dict:
    """Handle Click PREPARE request"""
    click_trans_id = str(payload.get("click_trans_id", ""))
    merchant_trans_id = str(payload.get("merchant_trans_id", ""))
    amount = str(payload.get("amount", "0"))
    action = str(payload.get("action", "0"))
    sign_time = str(payload.get("sign_time", ""))
    received_sign = str(payload.get("sign_string", ""))
    
    # Verify signature
    if not verify_click_signature(
        click_trans_id, service_id, secret_key,
        merchant_trans_id, amount, action, sign_time, received_sign
    ):
        logger.warning("Click signature verification failed")
        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "error": -1,
            "error_note": "Invalid signature"
        }
    
    # Check if order exists
    from services.database import db
    order = await db.get_order(merchant_trans_id)
    
    if not order:
        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "error": -5,
            "error_note": "Order not found"
        }
    
    # Check amount matches
    order_amount = float(order.get("amount", 0))
    click_amount = float(amount)
    
    if abs(order_amount - click_amount) > 0.01:
        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "error": -2,
            "error_note": "Invalid amount"
        }
    
    # Success
    return {
        "click_trans_id": click_trans_id,
        "merchant_trans_id": merchant_trans_id,
        "error": 0,
        "error_note": "Success"
    }


async def handle_click_complete(payload: dict, service_id: str, secret_key: str) -> dict:
    """Handle Click COMPLETE request - actual payment"""
    click_trans_id = str(payload.get("click_trans_id", ""))
    merchant_trans_id = str(payload.get("merchant_trans_id", ""))
    amount = str(payload.get("amount", "0"))
    action = str(payload.get("action", "1"))
    sign_time = str(payload.get("sign_time", ""))
    received_sign = str(payload.get("sign_string", ""))
    error = int(payload.get("error", 0))
    
    # Verify signature
    if not verify_click_signature(
        click_trans_id, service_id, secret_key,
        merchant_trans_id, amount, action, sign_time, received_sign
    ):
        logger.warning("Click signature verification failed")
        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "error": -1,
            "error_note": "Invalid signature"
        }
    
    # Check if payment was successful
    if error != 0:
        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "error": -6,
            "error_note": "Transaction cancelled"
        }
    
    from services.database import db, add_balance, record_payment
    
    # Get order
    order = await db.get_order(merchant_trans_id)
    if not order:
        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "error": -5,
            "error_note": "Order not found"
        }
    
    user_id = order.get("telegram_id")
    amount_int = int(float(amount))
    
    # Record payment (prevent duplicates)
    inserted = await record_payment(
        merchant_trans_id,
        user_id,
        amount_int,
        "paid",
        f"Click: {click_trans_id}"
    )
    
    if not inserted:
        # Already processed
        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "error": -4,
            "error_note": "Already paid"
        }
    
    # Add balance
    new_balance = await add_balance(user_id, amount_int)
    
    # Send notification
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from bot.config import settings
    
    if settings.bot_token:
        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        try:
            await bot.send_message(
                user_id,
                f"✅ <b>To'lov muvaffaqiyatli!</b>\n\n"
                f"💰 Hisob to'ldirildi: <b>{amount_int:,}</b> so'm\n"
                f"📊 Yangi balans: <b>{new_balance:,}</b> so'm\n\n"
                f"🔢 Tranzaksiya: <code>{click_trans_id}</code>"
            )
        except Exception as e:
            logger.warning("Could not notify user %s: %s", user_id, e)
        finally:
            await bot.session.close()
    
    logger.info("Click payment completed: order=%s, amount=%s, user=%s", 
                merchant_trans_id, amount_int, user_id)
    
    return {
        "click_trans_id": click_trans_id,
        "merchant_trans_id": merchant_trans_id,
        "error": 0,
        "error_note": "Success"
    }
