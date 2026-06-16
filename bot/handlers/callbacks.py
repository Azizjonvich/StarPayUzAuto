from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.keyboards import main_inline_keyboard, topup_back_keyboard, topup_payment_keyboard
from bot.handlers.start import menu_text
from services.database import ensure_user, get_user, get_user_orders, db

import logging
logger = logging.getLogger(__name__)

router = Router()

STATUS_UZ = {
  "pending": "⏳ Kutilmoqda",
  "completed": "✅ Bajarildi",
  "failed": "❌ Xato",
  "paid": "✅ To'langan",
}

TASHKENT_OFFSET = timedelta(hours=5)
TIMEOUT_MINUTES = 5


class TopupStates(StatesGroup):
    waiting_amount = State()


def tashkent_now() -> datetime:
    """Return current time in Tashkent (UTC+5)"""
    return datetime.utcnow() + TASHKENT_OFFSET


def format_time(dt: datetime) -> str:
    return dt.strftime("%H:%M:%S")


@router.callback_query(F.data == "orders")
async def cb_orders(query: CallbackQuery) -> None:
  if not query.from_user:
    return
  orders = await get_user_orders(query.from_user.id)
  if not orders:
    text = "📦 Hozircha buyurtmalar yo'q."
  else:
    lines = ["📦 <b>Buyurtmalarim:</b>\n"]
    for o in orders:
      st = STATUS_UZ.get(o["status"], o["status"])
      qty = o.get("quantity") or "—"
      lines.append(
        f"• #{o['id']} {o['product_type']} → @{o['target_username']} "
        f"({qty}) — {st}"
      )
    text = "\n".join(lines)
  await query.message.answer(text, parse_mode="HTML")
  await query.answer()


@router.callback_query(F.data == "referrals")
async def cb_referrals(query: CallbackQuery) -> None:
  if not query.from_user or not query.bot:
    return
  user = await get_user(query.from_user.id) or await ensure_user(
    query.from_user.id, query.from_user.username, query.from_user.full_name
  )
  me = await query.bot.get_me()
  link = f"https://t.me/{me.username}?start={query.from_user.id}"
  await query.message.answer(
    f"👥 <b>Referallar:</b> {user.get('referrals', 0)} ta\n\n"
    f"Sizning havolangiz:\n<code>{link}</code>\n\n"
    f"Do'stlaringizni taklif qiling va bonus oling!",
    parse_mode="HTML",
  )
  await query.answer()


@router.callback_query(F.data == "topup")
async def cb_topup(query: CallbackQuery, state: FSMContext) -> None:
  """Ask user to enter amount"""
  if not query.from_user:
    return
  user_id = query.from_user.id
  user = await get_user(user_id)
  balance = user["balance"] if user else 0

  text = (
    f"💰 <b>Balansni to'ldirish</b>\n\n"
    f"Quyidagi miqdorni kiriting:\n\n"
    f"🔻Minimal: 1 000 so'm\n"
    f"🔺Maksimal: 2 500 000 so'm"
  )
  await query.message.edit_text(text, parse_mode="HTML", reply_markup=topup_back_keyboard())
  await state.set_state(TopupStates.waiting_amount)
  await query.answer()


@router.message(TopupStates.waiting_amount)
async def process_topup_amount(message: Message, state: FSMContext) -> None:
  """Process entered amount — create order via ElderPay (auto-detects payments)"""
  if not message.from_user or not message.text:
    return

  try:
    amount = int(message.text.replace(",", "").replace(" ", ""))
  except ValueError:
    await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting.")
    return

  if amount < 1000:
    await message.answer("❌ Minimal summa: 1 000 so'm. Qayta urinib ko'ring.")
    return
  if amount > 2500000:
    await message.answer("❌ Maksimal summa: 2 500 000 so'm. Qayta urinib ko'ring.")
    return

  await state.clear()

  user_id = message.from_user.id
  user = await get_user(user_id)
  if not user:
    await message.answer("❌ Foydalanuvchi topilmadi! /start bosing.")
    return

  # Create order via ElderPay (Node.js server)
  from services import payment_client
  result = await payment_client.create_elderpay_order(user_id, amount)

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
    f"🆔 Buyurtma: <code>{order_id}</code>\n"
    f"💰 Miqdori: {int(amount):,} so'm\n\n"
    f"💳 <b>To'lov uchun karta:</b>\n"
    f"<code>{card_number}</code>\n"
    f"👤 {card_owner}\n\n"
    f"⏰ Muddat: {format_time(now)} — {format_time(expires_at)} (Toshkent)\n"
    f"Aniq {TIMEOUT_MINUTES} daqiqa. To'lov avtomatik tekshiriladi!"
  )

  await message.answer(
    card_text,
    parse_mode="HTML",
    reply_markup=topup_payment_keyboard(order_id),
  )


@router.callback_query(F.data.startswith("check_payment_"))
async def cb_check_payment(query: CallbackQuery) -> None:
  """Check payment status via ElderPay (Node.js server)"""
  if not query.from_user:
    return
  await query.answer("Tekshirilmoqda...")

  order_id = query.data.split("_", 2)[2]

  # Check via ElderPay through Node.js server
  from services import payment_client
  result = await payment_client.check_elderpay_order(order_id)

  if result.get("success") and result.get("data", {}).get("paid"):
    data = result["data"]
    amount = data.get("amount", 0)
    new_balance = data.get("new_balance", 0)

    await query.message.edit_text(
      f"✅ <b>To'lov muvaffaqiyatli!</b>\n\n"
      f"Hisobingizga {amount:,} so'm qo'shildi.\n"
      f"Yangi balans: {new_balance:,} so'm",
      parse_mode="HTML"
    )
    await query.message.answer(
      "🏠 Bosh menyu:", reply_markup=main_inline_keyboard()
    )
  else:
    await query.answer(
      "⏳ To'lov hali amalga oshmagan.\n\n"
      "💡 Pul o'tkazgan bo'lsangiz, bir necha daqiqadan so'ng qayta tekshiring.\n\n"
      "Pul tushgach, avtomatik tarzda hisobingizga qo'shiladi.",
      show_alert=True,
    )


@router.callback_query(F.data.startswith("cancel_order_"))
async def cb_cancel_order(query: CallbackQuery) -> None:
  """Cancel order"""
  if not query.from_user:
    return
  await query.answer()
  order_id = query.data.split("_", 2)[2]
  order = await db.get_order(order_id)
  if order and order['status'] == "pending":
    await db.update_order(order_id, status="cancelled")
  await query.message.edit_text("❌ Buyurtma bekor qilindi.", parse_mode="HTML")
  await query.message.answer("🏠 Bosh menyu:", reply_markup=main_inline_keyboard())


@router.callback_query(F.data == "topup_back")
async def cb_topup_back(query: CallbackQuery, state: FSMContext) -> None:
  """Go back from topup — clear state and return to main menu"""
  await state.clear()
  await cb_refresh(query)


@router.callback_query(F.data == "refresh_menu")
async def cb_refresh(query: CallbackQuery) -> None:
  if not query.from_user or not query.message:
    return
  user = await get_user(query.from_user.id) or await ensure_user(
    query.from_user.id, query.from_user.username, query.from_user.full_name
  )
  await query.message.edit_text(
    menu_text(
      user,
      query.from_user.username,
      query.from_user.first_name,
    ),
    reply_markup=main_inline_keyboard(),
  )
  await query.answer("Yangilandi")
