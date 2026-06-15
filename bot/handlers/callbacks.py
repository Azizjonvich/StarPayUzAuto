import uuid
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.keyboards import main_inline_keyboard, topup_back_keyboard
from bot.handlers.start import menu_text
from api_client import api_client
from services.database import ensure_user, get_user, get_user_orders, db, get_pool

router = Router()

STATUS_UZ = {
  "pending": "⏳ Kutilmoqda",
  "completed": "✅ Bajarildi",
  "failed": "❌ Xato",
  "paid": "✅ To'langan",
}


class TopupStates(StatesGroup):
    waiting_amount = State()


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
  """Process entered amount and show payment info"""
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

  # Create order
  order_id = f"topup_{uuid.uuid4().hex[:8]}"
  await db.create_order(order_id, user_id, "topup", amount, amount)

  # Create payment via Fragment API
  callback_url = f"{settings.api_public_url}/webhook/payment"
  redirect_url = f"{settings.api_public_url}/payment/success"

  try:
    payment_result = await api_client.create_payment(
      amount=int(amount),
      order_id=order_id,
      user_id=user_id,
      description=f"Hisobni to'ldirish - {int(amount):,} so'm",
      callback_url=callback_url,
      redirect_url=redirect_url,
    )
  except Exception as e:
    import logging
    logging.getLogger(__name__).exception("create_payment error")
    await message.answer("❌ To'lov yaratishda xatolik yuz berdi. Qayta urinib ko'ring.", reply_markup=main_inline_keyboard())
    return

  if payment_result and (payment_result.get("ok") or payment_result.get("success") or payment_result.get("payment_url")):
    payment_url = payment_result.get("payment_url")
    await db.update_order(order_id, payment_url=payment_url)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    payment_kb = InlineKeyboardMarkup(inline_keyboard=[
      [InlineKeyboardButton(text="💳 To'lash", url=payment_url)],
      [InlineKeyboardButton(text="✅ To'lovni tekshirish", callback_data=f"check_payment_{order_id}")],
      [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_order_{order_id}")],
    ])

    await message.answer(
      f"✅ <b>To'lov so'rovi yaratildi!</b>\n\n"
      f"🆔 Buyurtma: <code>{order_id}</code>\n"
      f"💰 Miqdori: {int(amount):,} so'm\n\n"
      f"💳 Quyidagi tugma orqali to'lovni amalga oshiring:",
      parse_mode="HTML",
      reply_markup=payment_kb,
    )
  else:
    await message.answer(
      "❌ To'lov yaratishda xatolik yuz berdi. Qayta urinib ko'ring.",
      reply_markup=main_inline_keyboard(),
    )


@router.callback_query(F.data.startswith("check_payment_"))
async def cb_check_payment(query: CallbackQuery) -> None:
  """Check payment status"""
  if not query.from_user:
    return
  await query.answer("Tekshirilmoqda...")

  order_id = query.data.split("_", 2)[2]

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
  else:
    await query.answer(
      "⏳ To'lov hali amalga oshmagan. Iltimos, avval to'lovni bajaring.",
      show_alert=True
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
