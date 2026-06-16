import uuid
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.keyboards import main_inline_keyboard, topup_back_keyboard, topup_payment_keyboard
from bot.handlers.start import menu_text
from services.database import ensure_user, get_user, get_user_orders, db, get_pool
from services.elderpay import ElderPayAPI, ElderPayError

import logging
logger = logging.getLogger(__name__)

router = Router()

STATUS_UZ = {
  "pending": "⏳ Kutilmoqda",
  "completed": "✅ Bajarildi",
  "failed": "❌ Xato",
  "paid": "✅ To'langan",
}

CARD_NUMBER = "9860180101712578"
TASHKENT_OFFSET = timedelta(hours=5)
TIMEOUT_MINUTES = 5

# ElderPay client — используем те же shop_id/shop_key (или отдельные ELDERPAY_* переменные)
elderpay = ElderPayAPI(
    shop_id=settings.elderpay_shop_id,
    shop_key=settings.elderpay_shop_key,
    api_url=settings.elderpay_api_url,
)


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
  """Process entered amount and show card payment info"""
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

  # Создаём order_id для локальной БД
  order_id = f"topup_{uuid.uuid4().hex[:10]}"

  # Создаём заказ в ElderPay (если настроен) — ДО сохранения в БД, чтобы сразу сохранить elderpay_order_id
  elderpay_order_id = None
  elderpay_error = None
  if elderpay.is_configured:
    try:
      result = await elderpay.create_order(amount)
      elderpay_order_id = result.get("order")
      logger.info(
        "ElderPay order created: local=%s elderpay=%s amount=%s",
        order_id, elderpay_order_id, amount,
      )
    except ElderPayError as e:
      elderpay_error = str(e)
      logger.warning("ElderPay create failed for %s: %s", user_id, elderpay_error)
  else:
    logger.info("ElderPay not configured — skipping create_order")

  # Сохраняем заказ в БД вместе с elderpay_order_id
  await db.create_order(order_id, user_id, "topup", amount, amount, elderpay_order_id=elderpay_order_id)

  # Calculate 5-minute window (Tashkent time)
  now = tashkent_now()
  expires_at = now + timedelta(minutes=TIMEOUT_MINUTES)

  card_text = (
    f"✅ <b>To'lov so'rovi yaratildi!</b>\n\n"
    f"🆔 Buyurtma: <code>{order_id}</code>\n"
    f"💰 Miqdori: {int(amount):,} so'm\n\n"
    f"💳 <b>To'lov uchun karta:</b>\n"
    f"<code>{CARD_NUMBER}</code>\n\n"
    f"⏰ Muddat: {format_time(now)} — {format_time(expires_at)} (Toshkent)\n"
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
    reply_markup=topup_payment_keyboard(order_id),
  )


@router.callback_query(F.data.startswith("check_payment_"))
async def cb_check_payment(query: CallbackQuery) -> None:
  """Check payment status — сначала ElderPay, потом локальная БД"""
  if not query.from_user:
    return
  await query.answer("Tekshirilmoqda...")

  order_id = query.data.split("_", 2)[2]
  order = await db.get_order(order_id)

  # ── 1. Проверка через ElderPay (если настроен и есть elderpay_order_id) ──
  check_id = order.get("elderpay_order_id") if order else None
  if elderpay.is_configured and check_id:
    try:
      result = await elderpay.check_order(check_id)
      elderpay_data = result.get("data", result)
      elderpay_status = (
        elderpay_data.get("status", "").lower().strip()
        if isinstance(elderpay_data, dict)
        else str(elderpay_data).lower().strip()
      )

      logger.info(
        "ElderPay check: order=%s elderpay_id=%s status=%s",
        order_id, check_id, elderpay_status,
      )

      if elderpay_status == "paid":
        await _credit_user(query, order)
        return
      elif elderpay_status == "cancel":
        await query.answer(
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
      await _credit_user(query, order)
    else:
      await query.answer("✅ To'lov allaqachon tasdiqlangan.", show_alert=True)
  else:
    elderpay_note = ""
    if elderpay.is_configured:
      elderpay_note = "\n\nElderPay orqali ham tekshirildi — to'lov topilmadi."
    await query.answer(
      f"⏳ To'lov hali amalga oshmagan. Iltimos, avval to'lovni bajaring.{elderpay_note}",
      show_alert=True,
    )


async def _credit_user(query: CallbackQuery, order: dict) -> None:
  """Credit balance to user and update order status."""
  await db.update_order(order.get("external_id") or order.get("id"), status="completed")
  await db.update_balance(order['telegram_id'], order['amount'], 'add')
  user = await get_user(order['telegram_id'])
  await query.message.edit_text(
    f"✅ <b>To'lov muvaffaqiyatli!</b>\n\n"
    f"Hisobingizga {order['amount']:,.0f} so'm qo'shildi.\n"
    f"Yangi balans: {user['balance']:,.0f} so'm",
    parse_mode="HTML"
  )
  await query.message.answer(
    "🏠 Bosh menyu:", reply_markup=main_inline_keyboard()
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
