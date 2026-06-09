from aiogram import F, Router
from aiogram.types import Message

from bot.keyboards import main_inline_keyboard
from bot.handlers.start import menu_text
from services.database import ensure_user, get_user, set_language

router = Router()

PRICES_TEXT = """
💰 <b>Narxlar</b>

⭐ <b>Telegram Stars</b> — Fragment bo'yicha joriy narx
💎 <b>Premium</b> — 3 / 6 / 12 oy
🎁 <b>Gift</b> — tanlangan gift bo'yicha
📞 <b>Virtual nomer</b> — mamlakat bo'yicha

Aniq narxlar Web App ichida ko'rsatiladi.
"""

GUIDE_TEXT = """
📚 <b>Qo'llanma</b>

1️⃣ Kerakli bo'limni tanlang (Stars, Premium, Gift yoki Nomer)
2️⃣ Web App ochiladi — @username va miqdorni kiriting
3️⃣ Buyurtma tasdiqlang
4️⃣ Natija «Buyurtmalarim» da ko'rinadi

💸 Balansni to'ldirish — «Hisobni to'ldirish» tugmasi
👥 Do'stlarni taklif qiling — «Referallar»
"""


@router.message(F.text.in_({"Narxlar", "💰 Narxlar"}))
async def reply_prices(message: Message) -> None:
  await message.answer(PRICES_TEXT, parse_mode="HTML")


@router.message(F.text.in_({"Qo'llanma", "📚 Qo'llanma"}))
async def reply_guide(message: Message) -> None:
  await message.answer(GUIDE_TEXT, parse_mode="HTML")


@router.message(F.text.in_({"Tilni almashtirish", "🔄 Tilni almashtirish"}))
async def reply_language(message: Message) -> None:
  if not message.from_user:
    return
  user = await get_user(message.from_user.id)
  current = (user or {}).get("language", "uz")
  new_lang = "ru" if current == "uz" else "uz"
  await ensure_user(
    message.from_user.id,
    message.from_user.username,
    message.from_user.full_name,
  )
  await set_language(message.from_user.id, new_lang)
  label = "Русский" if new_lang == "ru" else "O'zbek"
  await message.answer(f"🔄 Til o'zgartirildi: {label}")

  user = await get_user(message.from_user.id)
  if user:
    await message.answer(
      menu_text(
        user,
        message.from_user.username,
        message.from_user.first_name,
      ),
      reply_markup=main_inline_keyboard(),
    )
