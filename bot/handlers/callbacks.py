from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config import settings
from bot.keyboards import main_inline_keyboard
from bot.handlers.start import menu_text
from services.database import ensure_user, get_user, get_user_orders

router = Router()

STATUS_UZ = {
  "pending": "⏳ Kutilmoqda",
  "completed": "✅ Bajarildi",
  "failed": "❌ Xato",
  "paid": "✅ To'langan",
}


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
async def cb_topup(query: CallbackQuery) -> None:
  if not query.from_user:
    return
  await query.message.answer(
    f"💸 <b>Hisobni to'ldirish</b>\n\n"
    f"Shop ID: <code>{settings.shop_id}</code>\n"
    f"To'lov tizimi orqali to'lang — balans avtomatik yangilanadi.\n\n"
    f"To'lovda Telegram ID ni ko'rsating: <code>{query.from_user.id}</code>",
    parse_mode="HTML",
  )
  await query.answer()


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
