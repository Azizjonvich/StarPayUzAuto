from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

import config
import keyboards
from services.database import db
from services import payment_client

import logging
logger = logging.getLogger(__name__)

router = Router()

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
        f'<tg-emoji emoji-id="{config.CUSTOM_EMOJI_MONEY}">💰</tg-emoji> '
        f"<b>Balansni to'ldirish</b>\n\n"
        f"Quyidagi miqdorni kiriting:\n\n"
        f'<tg-emoji emoji-id="{config.CUSTOM_EMOJI_DOWN}">⬇️</tg-emoji> '
        f"Minimal: 1 000 so'm\n"
        f'<tg-emoji emoji-id="{config.CUSTOM_EMOJI_UP}">⬆️</tg-emoji> '
        f"Maksimal: 2 500 000 so'm"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=keyboards.get_back_keyboard())
    await state.set_state(BalanceStates.waiting_amount)


@router.message(BalanceStates.waiting_amount)
async def process_topup_amount(message: Message, state: FSMContext):
    """Process top-up amount — create order via ElderPay (auto-detects payments)"""
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

        # Create order via ElderPay (Node.js server)
        result = await payment_client.create_elderpay_order(user_id, int(amount))

        if not result.get("success"):
            error = result.get("error", "Noma'lum xatolik")
            logger.error("ElderPay create failed: %s", error)
            await message.answer(
                f"❌ To'lov so'rovini yaratishda xatolik: {error}\n\n"
                f"Iltimos, keyinroq urinib ko'ring yoki @StarPayUzAdmin ga murojaat qiling."
            )
            return

        data = result["data"]
        order_id = data["order_id"]
        card_number = data.get("card_number", "9860 1801 0171 2578")
        card_owner = data.get("card_owner", "Isxakova A.")
        expires_in = data.get("expires_in", 300)

        # Calculate expiration time
        now = tashkent_now()
        expires_at = now + timedelta(seconds=expires_in)

        card_text = (
            f"✅ <b>To'lov so'rovi yaratildi!</b>\n\n"
            f'<tg-emoji emoji-id="{config.CUSTOM_EMOJI_ID}">🆔</tg-emoji> '
            f"Buyurtma: <code>{order_id}</code>\n"
            f'<tg-emoji emoji-id="{config.CUSTOM_EMOJI_MONEY}">💰</tg-emoji> '
            f"Miqdori: {int(amount):,} so'm\n\n"
            f'<tg-emoji emoji-id="{config.CUSTOM_EMOJI_CARD}">💳</tg-emoji> '
            f"<b>To'lov uchun karta:</b>\n"
            f"<code>{card_number}</code>\n"
            f'<tg-emoji emoji-id="{config.CUSTOM_EMOJI_USER}">👤</tg-emoji> '
            f"{card_owner}\n\n"
            f'<tg-emoji emoji-id="{config.CUSTOM_EMOJI_CLOCK}">⏰</tg-emoji> '
            f"Pul o'tkazing. To'lov avtomatik tarzda tekshiriladi!\n"
            f"Pul tushgach, sizga xabar keladi va balansingizga qo'shiladi.\n\n"
            f'<tg-emoji emoji-id="{config.CUSTOM_EMOJI_WARN}">⚠️</tg-emoji> '
            f"Muddat: {format_time(now)} — {format_time(expires_at)} (Toshkent)\n"
            f"Aniq {TIMEOUT_MINUTES} daqiqa."
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
    """Check payment status via ElderPay (Node.js server)"""
    await callback.answer("Tekshirilmoqda...")

    order_id = callback.data.split("_", 2)[2]

    # Check via ElderPay through Node.js server
    result = await payment_client.check_elderpay_order(order_id)

    if result.get("success") and result.get("data", {}).get("paid"):
        data = result["data"]
        amount = data.get("amount", 0)
        new_balance = data.get("new_balance", 0)

        await callback.message.edit_text(
            f"✅ <b>To'lov muvaffaqiyatli!</b>\n\n"
            f"Hisobingizga {amount:,} so'm qo'shildi.\n"
            f"Yangi balans: {new_balance:,} so'm",
            parse_mode="HTML"
        )
        await callback.message.answer(
            "🏠 Bosh menyu:",
            reply_markup=keyboards.get_webapp_main_keyboard()
        )
    else:
        await callback.answer(
            "⏳ To'lov hali amalga oshmagan.\n\n"
            "💡 Pul o'tkazgan bo'lsangiz, bir necha daqiqadan so'ng qayta tekshiring.\n\n"
            "Pul tushgach, avtomatik tarzda hisobingizga qo'shiladi.",
            show_alert=True
        )


@router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order_handler(callback: CallbackQuery):
    """Cancel order — shows timeout message with premium emoji"""
    await callback.answer()

    order_id = callback.data.split("_", 2)[2]
    order = await db.get_order(order_id)

    if order and order['status'] == "pending":
        await db.update_order(order_id, status="cancelled")

    text = (
        f'<tg-emoji emoji-id="{config.CUSTOM_EMOJI_WARN2}">⚠️</tg-emoji> '
        f"<b>To'lov muddati tugadi!</b>\n\n"
        f'<tg-emoji emoji-id="{config.CUSTOM_EMOJI_CLOCK}">⏰</tg-emoji> '
        f"5 daqiqa ichida to'lov amalga oshirilmaganligi sababli\n"
        f'<tg-emoji emoji-id="{config.CUSTOM_EMOJI_ID}">🆔</tg-emoji> '
        f"<code>{order_id}</code> buyurtmangiz\n"
        f"avtomatik bekor qilindi.\n\n"
        f"Qaytadan urinib ko'ring."
    )

    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.message.answer(
        "🏠 Bosh menyu:",
        reply_markup=keyboards.get_bosh_menu_keyboard(),
    )
