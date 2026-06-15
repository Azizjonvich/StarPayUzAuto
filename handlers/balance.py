from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import uuid

import keyboards
from services.database import db, get_pool
from api_client import api_client
from bot.config import settings

import logging
logger = logging.getLogger(__name__)

router = Router()

CARD_NUMBER = "9860180101712578"
TASHKENT_OFFSET = timedelta(hours=5)
TIMEOUT_MINUTES = 5


class BalanceStates(StatesGroup):
    waiting_amount = State()


def tashkent_now() -> datetime:
    """Return current time in Tashkent (UTC+5)"""
    return datetime.utcnow() + TASHKENT_OFFSET


def format_time(dt: datetime) -> str:
    return dt.strftime("%H:%M:%S")


@router.message(F.text == "✨ Hisobni to'ldirish")
async def topup_menu(message: Message, state: FSMContext):
    """Show balance top-up menu"""
    user_id = message.from_user.id

    user = await db.get_user(user_id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi!")
        return

    text = (
        f"💰 <b>Balansni to'ldirish</b>\n\n"
        f"Quyidagi miqdorni kiriting:\n\n"
        f"🔻Minimal: 1 000 so'm\n"
        f"🔺Maksimal: 2 500 000 so'm"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=keyboards.get_back_keyboard())
    await state.set_state(BalanceStates.waiting_amount)


@router.message(BalanceStates.waiting_amount)
async def process_topup_amount(message: Message, state: FSMContext):
    """Process top-up amount and show card payment info"""
    try:
        amount = float(message.text.replace(",", "").replace(" ", ""))

        if amount < 1000:
            await message.answer("❌ Minimal summa: 1 000 so'm. Qayta urinib ko'ring.")
            return

        if amount > 2500000:
            await message.answer("❌ Maksimal summa: 2 500 000 so'm. Qayta urinib ko'ring.")
            return

        await state.clear()

        user_id = message.from_user.id
        order_id = f"topup_{uuid.uuid4().hex[:10]}"

        # Create order in database (external_id = order_id for webhook matching)
        await db.create_order(order_id, user_id, "topup", int(amount), amount)

        # Register order with StarPayUz (non-blocking — card always shown)
        try:
            callback_url = f"{settings.api_public_url}/webhook/payment"
            redirect_url = f"{settings.api_public_url}/payment/success"
            pay_result = await api_client.create_payment(
                amount=int(amount),
                order_id=order_id,
                user_id=user_id,
                description=f"StarPayUz - Hisobni to'ldirish {int(amount):,} so'm",
                callback_url=callback_url,
                redirect_url=redirect_url,
            )
            logger.info("create_payment for %s: %s", order_id, pay_result)
        except Exception as e:
            logger.warning("create_payment failed for %s: %s", order_id, e)

        # Calculate 5-minute window (Tashkent time)
        now = tashkent_now()
        expires_at = now + timedelta(minutes=TIMEOUT_MINUTES)

        text = (
            f"✅ <b>To'lov so'rovi yaratildi!</b>\n\n"
            f"🆔 Buyurtma: <code>{order_id}</code>\n"
            f"💰 Miqdori: {int(amount):,} so'm\n\n"
            f"💳 <b>To'lov uchun karta:</b>\n"
            f"<code>{CARD_NUMBER}</code>\n\n"
            f"⏰ To'lov amalga oshirilgach, quyidagi tugmani bosing "
            f"yoki bot avtomatik aniqlaydi.\n\n"
            f"⚠️ Muddat: {format_time(now)} — {format_time(expires_at)} (Toshkent)\n"
            f"Aniq {TIMEOUT_MINUTES} daqiqa. Undan keyin avtomatik bekor qilinadi!"
        )

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboards.get_card_payment_keyboard(order_id),
        )

    except ValueError:
        await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting.")


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_status(callback: CallbackQuery):
    """Check payment status — local DB table + StarPayUz API"""
    await callback.answer("Tekshirilmoqda...")

    order_id = callback.data.split("_", 2)[2]

    # 1. Check local payments table
    pool = await get_pool()
    async with pool.acquire() as conn:
        payment = await conn.fetchrow(
            "SELECT * FROM payments WHERE shop_order_id = $1 AND status = 'paid'",
            order_id
        )

    if payment:
        order = await db.get_order(order_id)
        if order and order['status'] == "pending":
            await db.update_order(order_id, status="completed")
            await db.update_balance(order['telegram_id'], order['amount'], 'add')
            user = await db.get_user(order['telegram_id'])
            await callback.message.edit_text(
                f"✅ <b>To'lov muvaffaqiyatli!</b>\n\n"
                f"Hisobingizga {order['amount']:,.0f} so'm qo'shildi.\n"
                f"Yangi balans: {user['balance']:,.0f} so'm",
                parse_mode="HTML"
            )
            await callback.message.answer(
                "🏠 Bosh menyu:",
                reply_markup=keyboards.get_webapp_main_keyboard()
            )
        return

    # 2. Not found locally — try StarPayUz API
    try:
        api_result = await api_client.check_payment(order_id)
        logger.info("StarPayUz check_payment for %s: %s", order_id, api_result)
        if api_result.get("ok") and api_result.get("paid"):
            order = await db.get_order(order_id)
            if order and order['status'] == "pending":
                from services.database import record_payment
                amount = int(api_result.get("amount", order['amount']))
                await record_payment(order_id, order['telegram_id'], amount, "paid", f"starPayUz:{api_result}")
                await db.update_order(order_id, status="completed")
                await db.update_balance(order['telegram_id'], amount, 'add')
                user = await db.get_user(order['telegram_id'])
                await callback.message.edit_text(
                    f"✅ <b>To'lov muvaffaqiyatli!</b>\n\n"
                    f"Hisobingizga {amount:,.0f} so'm qo'shildi.\n"
                    f"Yangi balans: {user['balance']:,.0f} so'm",
                    parse_mode="HTML"
                )
                await callback.message.answer(
                    "🏠 Bosh menyu:",
                    reply_markup=keyboards.get_webapp_main_keyboard()
                )
                return
    except Exception as e:
        logger.warning("StarPayUz check_payment error: %s", e)

    # 3. Not found anywhere
    await callback.answer(
        "⏳ To'lov hali amalga oshmagan. Iltimos, avval to'lovni bajaring.",
        show_alert=True
    )


@router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order_handler(callback: CallbackQuery):
    """Cancel order"""
    await callback.answer()

    order_id = callback.data.split("_", 2)[2]
    order = await db.get_order(order_id)

    if order and order['status'] == "pending":
        await db.update_order(order_id, status="cancelled")

    await callback.message.edit_text(
        "❌ Buyurtma bekor qilindi.",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "🏠 Bosh menyu:",
        reply_markup=keyboards.get_webapp_main_keyboard()
    )
