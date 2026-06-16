from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import uuid

import keyboards
from services.database import db, get_pool
from services.elderpay import ElderPayAPI, ElderPayError

import logging
logger = logging.getLogger(__name__)

router = Router()

CARD_NUMBER = "9860180101712578"
TASHKENT_OFFSET = timedelta(hours=5)
TIMEOUT_MINUTES = 5

# ElderPay client — для автоматической проверки платежей
import config as bot_config
elderpay = ElderPayAPI(
    shop_id=bot_config.SHOP_ID or "",
    shop_key=bot_config.SHOP_KEY or "",
    api_url="https://elder.uz/api",
)


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
        elderpay_order_id = None
        elderpay_error = None

        # Создаём заказ в ElderPay (если настроен)
        if elderpay.is_configured:
            try:
                result = await elderpay.create_order(int(amount))
                elderpay_order_id = result.get("order") or str(result)
                logger.info(
                    "ElderPay order created: local=%s elderpay=%s amount=%s",
                    order_id, elderpay_order_id, int(amount),
                )
            except ElderPayError as e:
                elderpay_error = str(e)
                logger.warning("ElderPay create failed for %s: %s", user_id, elderpay_error)
        else:
            logger.info("ElderPay not configured — skipping create_order")

        # Сохраняем elderpay_order_id в БД
        await db.create_order(order_id, user_id, "topup", int(amount), amount, elderpay_order_id=elderpay_order_id)

        # Calculate 5-minute window (Tashkent time)
        now = tashkent_now()
        expires_at = now + timedelta(minutes=TIMEOUT_MINUTES)

        card_text = (
            f"✅ <b>To'lov so'rovi yaratildi!</b>\n\n"
            f"🆔 Buyurtma: <code>{order_id}</code>\n"
            f"💰 Miqdori: {int(amount):,} so'm\n\n"
            f"💳 <b>To'lov uchun karta:</b>\n"
            f"<code>{CARD_NUMBER}</code>\n\n"
            f"⏰ To'lov amalga oshirilgach, quyidagi tugmani bosing.\n\n"
            f"⚠️ Muddat: {format_time(now)} — {format_time(expires_at)} (Toshkent)\n"
            f"Aniq {TIMEOUT_MINUTES} daqiqa. Undan keyin avtomatik bekor qilinadi!"
        )

        if elderpay_error:
            card_text += (
                f"\n\n⚠️ ElderPay xatosi: {elderpay_error}\n"
                f"To'lovni amalga oshirib, «To'lovni tekshirish» tugmasini bosing."
            )
        elif elderpay.is_configured:
            card_text += (
                f"\n\n🤖 ElderPay orqali avtomatik tekshiriladi.\n"
                f"Pul tushgach, balans avtomatik to'ldiriladi!"
            )

        await message.answer(
            card_text,
            parse_mode="HTML",
            reply_markup=keyboards.get_card_payment_keyboard(order_id),
        )

    except ValueError:
        await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting.")


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_status(callback: CallbackQuery):
    """Check payment status — ElderPay API first, then local DB"""
    await callback.answer("Tekshirilmoqda...")

    order_id = callback.data.split("_", 2)[2]
    order = await db.get_order(order_id)

    # ── 1. Проверка через ElderPay (если настроен и есть elderpay_order_id) ──
    if elderpay.is_configured and order and order.get("elderpay_order_id"):
        try:
            result = await elderpay.check_order(order["elderpay_order_id"])
            elderpay_data = result.get("data", result)
            elderpay_status = (
                elderpay_data.get("status", "").lower().strip()
                if isinstance(elderpay_data, dict)
                else str(elderpay_data).lower().strip()
            )

            logger.info(
                "ElderPay check: order=%s elderpay_id=%s status=%s",
                order_id, order["elderpay_order_id"], elderpay_status,
            )

            if elderpay_status == "paid":
                await _credit_user(callback, order, order_id)
                return
            elif elderpay_status == "cancel":
                await callback.answer(
                    "❌ To'lov bekor qilingan. Qayta urinib ko'ring.",
                    show_alert=True,
                )
                return
        except ElderPayError as e:
            logger.warning("ElderPay check failed for %s: %s", order_id, e)
            # Продолжаем — проверяем локальную БД как fallback

    # ── 2. Fallback: проверка локальной БД (для webhook/Click/Payme) ──
    pool = await get_pool()
    async with pool.acquire() as conn:
        payment = await conn.fetchrow(
            "SELECT * FROM payments WHERE shop_order_id = $1 AND status = 'paid'",
            order_id
        )

    if payment:
        if order and order['status'] == "pending":
            await _credit_user(callback, order, order_id)
        else:
            await callback.answer("✅ To'lov allaqachon tasdiqlangan.", show_alert=True)
    else:
        elderpay_note = ""
        if elderpay.is_configured:
            elderpay_note = "\n\nElderPay orqali ham tekshirildi — to'lov topilmadi."
        await callback.answer(
            f"⏳ To'lov hali amalga oshmagan. Iltimos, avval to'lovni bajaring.{elderpay_note}",
            show_alert=True
        )


async def _credit_user(callback: CallbackQuery, order: dict, order_id: str) -> None:
    """Credit balance to user and update order status."""
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
