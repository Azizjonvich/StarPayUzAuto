from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from bot.config import settings
from bot.keyboards import bosh_menu_keyboard, main_inline_keyboard, stars_keyboard, premium_keyboard, topup_back_keyboard, topup_payment_keyboard
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

  money_emoji = settings.custom_emoji_money
  down_emoji = settings.custom_emoji_down
  up_emoji = settings.custom_emoji_up
  text = (
    f"<tg-emoji emoji-id=\"{money_emoji}\">💰</tg-emoji> "
    f"<b>Balansni to'ldirish</b>\n\n"
    f"Quyidagi miqdorni kiriting:\n\n"
    f"<tg-emoji emoji-id=\"{down_emoji}\">⬇️</tg-emoji> "
    f"Minimal: 1 000 so'm\n"
    f"<tg-emoji emoji-id=\"{up_emoji}\">⬆️</tg-emoji> "
    f"Maksimal: 2 500 000 so'm"
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

  id_emoji = settings.custom_emoji_id_icon
  money_emoji = settings.custom_emoji_money
  card_emoji = settings.custom_emoji_card
  user_emoji = settings.custom_emoji_user
  clock_emoji = settings.custom_emoji_clock
  warn_emoji = settings.custom_emoji_warn
  card_text = (
    f"✅ <b>To'lov so'rovi yaratildi!</b>\n\n"
    f"<tg-emoji emoji-id=\"{id_emoji}\">🆔</tg-emoji> "
    f"Buyurtma: <code>{order_id}</code>\n"
    f"<tg-emoji emoji-id=\"{money_emoji}\">💰</tg-emoji> "
    f"Miqdori: {int(amount):,} so'm\n\n"
    f"<tg-emoji emoji-id=\"{card_emoji}\">💳</tg-emoji> "
    f"<b>To'lov uchun karta:</b>\n"
    f"<code>{card_number}</code>\n"
    f"<tg-emoji emoji-id=\"{user_emoji}\">👤</tg-emoji> "
    f"{card_owner}\n\n"
    f"<tg-emoji emoji-id=\"{clock_emoji}\">⏰</tg-emoji> "
    f"Pul o'tkazing. To'lov avtomatik tarzda tekshiriladi!\n"
    f"Pul tushgach, sizga xabar keladi va balansingizga qo'shiladi.\n\n"
    f"<tg-emoji emoji-id=\"{warn_emoji}\">⚠️</tg-emoji> "
    f"Muddat: {format_time(now)} — {format_time(expires_at)} (Toshkent)\n"
    f"Aniq {TIMEOUT_MINUTES} daqiqa."
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

    check_emoji = f'<tg-emoji emoji-id="{settings.custom_emoji_check}">✅</tg-emoji>'
    wallet_emoji = f'<tg-emoji emoji-id="{settings.custom_emoji_wallet}">👛</tg-emoji>'
    money_emoji = f'<tg-emoji emoji-id="{settings.custom_emoji_money}">💰</tg-emoji>'

    text = (
      f"{check_emoji} <b>To'lov muvaffaqiyatli qabul qilindi</b>\n\n"
      f"{wallet_emoji} +{amount:,} so'm\n"
      f"{money_emoji} Balans: {new_balance:,} so'm"
    )

    await query.message.edit_text(text, parse_mode="HTML")
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
  """Cancel order — shows timeout message with premium emoji"""
  if not query.from_user:
    return
  await query.answer()
  order_id = query.data.split("_", 2)[2]
  order = await db.get_order(order_id)
  if order and order['status'] == "pending":
    await db.update_order(order_id, status="cancelled")

  text = (
    f'<tg-emoji emoji-id="{settings.custom_emoji_warn2}">⚠️</tg-emoji> '
    f"<b>To'lov muddati tugadi!</b>\n\n"
    f'<tg-emoji emoji-id="{settings.custom_emoji_clock}">⏰</tg-emoji> '
    f"5 daqiqa ichida to'lov amalga oshirilmaganligi sababli\n"
    f'<tg-emoji emoji-id="{settings.custom_emoji_id_icon}">🆔</tg-emoji> '
    f"<code>{order_id}</code> buyurtmangiz\n"
    f"avtomatik bekor qilindi.\n\n"
    f"Qaytadan urinib ko'ring."
  )

  await query.message.edit_text(text, parse_mode="HTML")
  await query.message.answer(
    "🏠 Bosh menyu:", reply_markup=bosh_menu_keyboard()
  )


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


# ─── Product menu callbacks ───────────────────────────────────────

@router.callback_query(F.data == "stars_menu")
async def cb_stars_menu(query: CallbackQuery) -> None:
  await query.answer()
  text = (
    f"<tg-emoji emoji-id=\"{settings.custom_emoji_star or '5807791714093502248'}\">⭐</tg-emoji> "
    f"<b>Telegram Stars sotib olish</b>\n\n"
    "Stars — Telegram ichida maxsus kontent va xizmatlarni "
    "sotib olish uchun ishlatiladi.\n\n"
    "📦 <b>Mavjud paketlar:</b>"
  )
  await query.message.edit_text(text, parse_mode="HTML", reply_markup=stars_keyboard())


@router.callback_query(F.data == "premium_menu")
async def cb_premium_menu(query: CallbackQuery) -> None:
  await query.answer()
  premium_emoji = settings.custom_emoji_premium or "6053186856688814091"
  text = (
    f"<tg-emoji emoji-id=\"{premium_emoji}\">💎</tg-emoji> "
    f"<b>Telegram Premium sotib olish</b>\n\n"
    "Premium obuna bilan qo'shimcha imkoniyatlarga ega bo'ling:\n\n"
    "✨ Tezroq yuklab olish tezligi\n"
    "📁 4 GB gacha fayllar\n"
    "🎨 Eksklyuziv stikerlar\n"
    "👤 Premium emoji va badge\n"
    "💬 Kengaytirilgan chat imkoniyatlari\n\n"
    "📦 <b>Mavjud paketlar:</b>"
  )
  await query.message.edit_text(text, parse_mode="HTML", reply_markup=premium_keyboard())


@router.callback_query(F.data == "gift_menu")
async def cb_gift_menu(query: CallbackQuery) -> None:
  await query.answer()
  gift_emoji = settings.custom_emoji_gift or "5348068314629315530"
  text = (
    f"<tg-emoji emoji-id=\"{gift_emoji}\">🎁</tg-emoji> "
    f"<b>Gift sovg'alar</b>\n\n"
    "Do'stlaringizga Telegram sovg'alarini yuboring!\n\n"
    "🎯 Giftlarni Web App orqali tanlang va yuboring.\n\n"
    "👇 Pastdagi tugma orqali magazinni oching:"
  )
  kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(
      text=f"🛒 Magazin ochish",
      web_app=WebAppInfo(url=f"{settings.webapp_base_url}/index.html")
    )],
    [InlineKeyboardButton(text="◀️ Orqaga", callback_data="refresh_menu")],
  ])
  await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "phone_menu")
async def cb_phone_menu(query: CallbackQuery) -> None:
  await query.answer()
  phone_emoji = settings.custom_emoji_phone or "📱"
  text = (
    f"<tg-emoji emoji-id=\"{phone_emoji}\">📱</tg-emoji> "
    f"<b>Virtual raqamlar</b>\n\n"
    "Tez orada mavjud bo'ladi...\n\n"
    "Bu bo'limda siz turli xizmatlar uchun "
    "virtual telefon raqamlarini sotib olishingiz mumkin bo'ladi."
  )
  await query.message.edit_text(text, parse_mode="HTML",
    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
      [InlineKeyboardButton(text="◀️ Orqaga", callback_data="refresh_menu")]
    ])
  )


# ─── Buy Stars callback ────────────────────────────────────────────

@router.callback_query(F.data.startswith("buy_stars_"))
async def cb_buy_stars(query: CallbackQuery) -> None:
  """Process stars purchase from inline keyboard"""
  await query.answer()
  if not query.from_user:
    return
  amount = int(query.data.split("_")[2])
  user_id = query.from_user.id

  price = None
  for a, p in [(50, 10000), (75, 15000), (100, 20000), (250, 50000), (500, 100000)]:
    if a == amount:
      price = p
      break

  if not price:
    await query.message.answer("❌ Xatolik yuz berdi!")
    return

  user = await get_user(user_id)
  if not user:
    await query.message.answer("❌ Foydalanuvchi topilmadi!")
    return

  if user["balance"] >= price:
    await db.update_balance(user_id, price, "subtract")
    import uuid
    order_id = str(uuid.uuid4())[:8]
    await db.create_order(order_id, user_id, "stars", amount, price)
    await db.update_order(order_id, status="processing")

    from services.fragment_api import fragment_client
    username = query.from_user.username or str(user_id)
    result = await fragment_client.buy_stars(username, amount)

    if result and result.get("ok"):
      await db.update_order(order_id, status="completed", completed_at=datetime.utcnow().isoformat())
      user = await get_user(user_id)
      await query.message.answer(
        f"✅ <b>Muvaffaqiyatli!</b>\n\n"
        f"⭐ {amount} Stars hisobingizga qo'shildi!\n"
        f"💰 Yangi balans: {user['balance']:,.0f} so'm",
        parse_mode="HTML",
      )
    else:
      await db.update_order(order_id, status="failed")
      await db.update_balance(user_id, price, "add")
      await query.message.answer("❌ Xatolik yuz berdi. Pul hisobingizga qaytarildi.")
  else:
    needed = price - user["balance"]
    await query.message.answer(
      f"💰 <b>Balans yetarli emas!</b>\n\n"
      f"Kerakli summa: {price:,.0f} so'm\n"
      f"Sizning balansingiz: {user['balance']:,.0f} so'm\n"
      f"Yetishmayotgan: {needed:,.0f} so'm",
      parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("buy_premium_"))
async def cb_buy_premium(query: CallbackQuery) -> None:
  """Process premium purchase from inline keyboard"""
  await query.answer()
  if not query.from_user:
    return
  duration = int(query.data.split("_")[2])
  user_id = query.from_user.id

  price = None
  for d, p, n in [(3, 160000, "3 oy"), (6, 225000, "6 oy"), (12, 380000, "12 oy")]:
    if d == duration:
      price = p
      break

  if not price:
    await query.message.answer("❌ Xatolik yuz berdi!")
    return

  user = await get_user(user_id)
  if not user:
    await query.message.answer("❌ Foydalanuvchi topilmadi!")
    return

  if user["balance"] >= price:
    await db.update_balance(user_id, price, "subtract")
    import uuid
    order_id = str(uuid.uuid4())[:8]
    await db.create_order(order_id, user_id, "premium", duration, price)
    await db.update_order(order_id, status="processing")

    from services.fragment_api import fragment_client
    username = query.from_user.username or str(user_id)
    result = await fragment_client.buy_premium(username, duration)

    if result and result.get("ok"):
      await db.update_order(order_id, status="completed", completed_at=datetime.utcnow().isoformat())
      user = await get_user(user_id)
      await query.message.answer(
        f"✅ <b>Muvaffaqiyatli!</b>\n\n"
        f"💎 Telegram Premium {duration} oyga faollashtirildi!\n"
        f"💰 Yangi balans: {user['balance']:,.0f} so'm",
        parse_mode="HTML",
      )
    else:
      await db.update_order(order_id, status="failed")
      await db.update_balance(user_id, price, "add")
      await query.message.answer("❌ Xatolik yuz berdi. Pul hisobingizga qaytarildi.")
  else:
    needed = price - user["balance"]
    await query.message.answer(
      f"💰 <b>Balans yetarli emas!</b>\n\n"
      f"Kerakli summa: {price:,.0f} so'm\n"
      f"Sizning balansingiz: {user['balance']:,.0f} so'm\n"
      f"Yetishmayotgan: {needed:,.0f} so'm",
      parse_mode="HTML",
    )
