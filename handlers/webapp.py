import json
import logging
import uuid
from datetime import datetime

from aiogram import F, Router
from aiogram.types import Message

import config
import keyboards
from api_client import api_client
from services.database import db

logger = logging.getLogger(__name__)
router = Router()


def _stars_price(amount: int, price_from_app: int | None) -> int:
    if price_from_app and price_from_app > 0:
        return price_from_app
    return int(amount * 10000 / 50)


def _parse_username(raw: str) -> str | None:
    username = (raw or "").strip().lstrip("@")
    return username or None


@router.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await message.answer("❌ Noto'g'ri ma'lumot formati.")
        return

    action = data.get("action")
    handlers = {
        "buy_stars": _buy_stars,
        "buy_premium": _buy_premium,
        "buy_gift": _buy_gift,
        "buy_phone": _buy_phone,
    }
    handler = handlers.get(action)  
    if not handler:
        await message.answer("❌ Noma'lum buyurtma turi.")
        return
    try:
        await handler(message, data)
    except Exception as e:
        logger.exception("Webapp handler xatoligi: %s", e)
        await message.answer(
            "❌ Ichki xatolik yuz berdi. Iltimos qayta urinib ko'ring yoki admin bilan bog'laning.",
            reply_markup=keyboards.get_webapp_main_keyboard(),
        )


async def _buy_stars(message: Message, data: dict):
    user_id = message.from_user.id
    username = _parse_username(data.get("username", ""))
    amount = int(data.get("amount", 0))
    price = _stars_price(amount, data.get("price"))

    if not username:
        await message.answer("❌ Username kiriting.")
        return
    if amount < config.STARS_MIN_AMOUNT or amount > config.STARS_MAX_AMOUNT:
        await message.answer(
            f"❌ Stars miqdori {config.STARS_MIN_AMOUNT:,} — {config.STARS_MAX_AMOUNT:,} orasida bo'lishi kerak."
        )
        return

    user = await db.get_user(user_id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi. /start bosing.")
        return
    if user["balance"] < price:
        await message.answer(
            f"💰 <b>Balans yetarli emas!</b>\n\n"
            f"Kerak: {price:,} so'm\n"
            f"Balans: {user['balance']:,.0f} so'm",
            parse_mode="HTML",
        )
        return

    order_id = str(uuid.uuid4())[:8]
    await db.update_balance(user_id, price, "subtract")
    await db.create_order(order_id, user_id, "stars", amount, price)
    await db.update_order(order_id, status="processing")

    result = await api_client.buy_stars(username, amount)
    if result and result.get("ok"):
        await db.update_order(
            order_id, status="completed", completed_at=datetime.utcnow().isoformat()
        )
        user = await db.get_user(user_id)
        await message.answer(
            f"✅ <b>Muvaffaqiyatli!</b>\n\n"
            f"⭐ <b>{amount}</b> Stars → @{username}\n"
            f"💰 Yangi balans: {user['balance']:,.0f} so'm",
            parse_mode="HTML",
            reply_markup=keyboards.get_webapp_main_keyboard(),
        )
    else:
        await db.update_order(order_id, status="failed")
        await db.update_balance(user_id, price, "add")
        err = result.get("message", "Noma'lum xatolik")
        await message.answer(
            f"❌ <b>Xatolik:</b> {err}\n\nPul qaytarildi.",
            parse_mode="HTML",
            reply_markup=keyboards.get_webapp_main_keyboard(),
        )


async def _buy_premium(message: Message, data: dict):
    user_id = message.from_user.id
    username = _parse_username(data.get("username", ""))
    duration = int(data.get("duration", 0))
    price = int(data.get("price", 0))

    if not username:
        await message.answer("❌ Username kiriting.")
        return
    if duration not in (3, 6, 12):
        await message.answer("❌ Davomiylikni tanlang (3, 6 yoki 12 oy).")
        return
    if price <= 0:
        for pkg in config.PRODUCTS["premium"]["packages"]:
            if pkg["duration"] == duration:
                price = pkg["price"]
                break

    user = await db.get_user(user_id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi. /start bosing.")
        return
    if user["balance"] < price:
        await message.answer(
            f"💰 <b>Balans yetarli emas!</b>\n\n"
            f"Kerak: {price:,} so'm\n"
            f"Balans: {user['balance']:,.0f} so'm",
            parse_mode="HTML",
        )
        return

    order_id = str(uuid.uuid4())[:8]
    await db.update_balance(user_id, price, "subtract")
    await db.create_order(order_id, user_id, "premium", duration, price)
    await db.update_order(order_id, status="processing")

    result = await api_client.buy_premium(username, duration)
    if result and result.get("ok"):
        await db.update_order(
            order_id, status="completed", completed_at=datetime.utcnow().isoformat()
        )
        user = await db.get_user(user_id)
        await message.answer(
            f"✅ <b>Muvaffaqiyatli!</b>\n\n"
            f"💎 Premium <b>{duration} oy</b> → @{username}\n"
            f"💰 Yangi balans: {user['balance']:,.0f} so'm",
            parse_mode="HTML",
            reply_markup=keyboards.get_webapp_main_keyboard(),
        )
    else:
        await db.update_order(order_id, status="failed")
        await db.update_balance(user_id, price, "add")
        err = result.get("message", "Noma'lum xatolik")
        await message.answer(
            f"❌ <b>Xatolik:</b> {err}\n\nPul qaytarildi.",
            parse_mode="HTML",
            reply_markup=keyboards.get_webapp_main_keyboard(),
        )


async def _buy_gift(message: Message, data: dict):
    user_id = message.from_user.id
    username = _parse_username(data.get("username", ""))
    gift = data.get("gift", "")
    price = int(data.get("price", 0))

    if not username:
        await message.answer("❌ Qabul qiluvchi username kiriting.")
        return
    if not gift or price <= 0:
        await message.answer("❌ Gift tanlang.")
        return

    user = await db.get_user(user_id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi. /start bosing.")
        return
    if user["balance"] < price:
        await message.answer(
            f"💰 <b>Balans yetarli emas!</b>\n\n"
            f"Kerak: {price:,} so'm\n"
            f"Balans: {user['balance']:,.0f} so'm",
            parse_mode="HTML",
        )
        return

    order_id = str(uuid.uuid4())[:8]
    await db.update_balance(user_id, price, "subtract")
    await db.create_order(order_id, user_id, "gift", 1, price)
    await db.update_order(order_id, status="processing")

    # Отправка подарка через Telethon
    from services.telethon_client import gift_sender
    
    logger.info(f"Gift sender status: {gift_sender}")

    if not gift_sender:
        logger.error("Gift sender not initialized - Telethon not configured")
        await db.update_order(order_id, status="failed")
        await db.update_balance(user_id, price, "add")
        await message.answer(
            f"❌ <b>Gift сервис временно недоступен</b>\n\n"
            f"⚠️ Telethon не настроен на сервере.\n"
            f"💰 Pul qaytarildi: <b>{price:,}</b> so'm\n\n"
            f"Iltimos, попробуйте позже или выберите другой продукт.",
            parse_mode="HTML",
            reply_markup=keyboards.get_webapp_main_keyboard(),
        )
        return

    # Маппинг подарков на их ID из Telegram
    gift_mapping = {
        "bear": "5170233102089322756",      # 🧸 15 💜
        "heart": "5170145012310081615",     # 💝 15 💜
        "box": "5170250947678437525",       # 🎁 25 💜
        "rose": "5168103777563050263",      # 🌹 25 💜
        "cake": "5170144170496491616",      # 🎂 50 💜
        "bouquet": "5170314324215857265",   # 💐 50 💜
        "rocket": "5170564780938756245",    # 🚀 50 💜
        "trophy": "5168043875654172773",    # 🏆 100 💜
        "ring": "5170690322832818290",      # 💍 100 💜
        "diamond": "5170521118301225164",   # 💎 100 💜
        "champagne": "6028601630662853006", # 🍾 50 💜
    }

    gift_id = gift_mapping.get(gift.lower())
    if not gift_id:
        logger.error(f"Unknown gift type: {gift}")
        await db.update_order(order_id, status="failed")
        await db.update_balance(user_id, price, "add")
        await message.answer(
            f"❌ <b>Noma'lum gift turi</b>\n\n"
            f"Gift: {gift}\n"
            f"💰 Pul qaytarildi: <b>{price:,}</b> so'm",
            parse_mode="HTML",
        )
        return

    logger.info(f"Sending gift {gift} (ID: {gift_id}) to @{username}")
    result = await gift_sender.send_gift(username, gift_id, message="🎁 Gift from StarPayUz")
    logger.info(f"Gift send result: {result}")

    if result and result.get("ok"):
        await db.update_order(
            order_id, status="completed", completed_at=datetime.utcnow().isoformat()
        )
        user = await db.get_user(user_id)
        await message.answer(
            f"🎉 <b>Muvaffaqiyatli!</b>\n\n"
            f"🎁 Gift yuborildi: <b>{gift.capitalize()}</b>\n"
            f"👤 Qabul qiluvchi: @{username}\n"
            f"💰 Yangi balans: <b>{user['balance']:,.0f}</b> so'm\n\n"
            f"✅ Gift darhol yetkazildi!",
            parse_mode="HTML",
            reply_markup=keyboards.get_webapp_main_keyboard(),
        )
    else:
        await db.update_order(order_id, status="failed")
        await db.update_balance(user_id, price, "add")
        err = result.get("error", "Noma'lum xatolik")
        await message.answer(
            f"❌ <b>Xatolik yuz berdi</b>\n\n"
            f"📝 Sabab: {err}\n"
            f"💰 Pul qaytarildi: <b>{price:,}</b> so'm\n\n"
            f"Iltimos, qayta urinib ko'ring yoki admin bilan bog'laning.",
            parse_mode="HTML",
            reply_markup=keyboards.get_webapp_main_keyboard(),
        )


async def _buy_phone(message: Message, data: dict):
    user_id = message.from_user.id
    username = _parse_username(data.get("username", ""))
    country = (data.get("country") or "UZ").upper()
    price = int(data.get("price", 50000))

    if not username:
        await message.answer("❌ Username kiriting.")
        return

    user = await db.get_user(user_id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi. /start bosing.")
        return
    if user["balance"] < price:
        await message.answer(
            f"💰 <b>Balans yetarli emas!</b>\n\n"
            f"Kerak: {price:,} so'm\n"
            f"Balans: {user['balance']:,.0f} so'm",
            parse_mode="HTML",
        )
        return

    order_id = str(uuid.uuid4())[:8]
    await db.update_balance(user_id, price, "subtract")
    await db.create_order(order_id, user_id, "phone", 1, price)
    await db.update_order(order_id, status="processing")

    await message.answer(
        f"✅ <b>Buyurtma qabul qilindi!</b>\n\n"
        f"📱 Virtual nomer ({country}) → @{username}\n"
        f"💰 Yangi balans: {(user['balance'] - price):,.0f} so'm\n\n"
        f"<i>Admin tez orada bog'lanadi.</i>",
        parse_mode="HTML",
        reply_markup=keyboards.get_webapp_main_keyboard(),
    )
