from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.keyboards import bottom_reply_keyboard, main_inline_keyboard
from services.database import ensure_user, get_user

router = Router()

EMOJI_WAVE = "5312345830382910731"  # 👋
EMOJI_MONEY = "5407091881219736716"  # 💰
EMOJI_PEOPLE = "5879905000972358125"  # 👥
EMOJI_LIGHTNING = "5224496844188458905"  # ⚡️


def menu_text(user: dict, display_name: str) -> str:
  balance = user.get("balance", 0)
  refs = user.get("referrals", 0)
  return (
    f'<tg-emoji emoji-id="{EMOJI_WAVE}">👋</tg-emoji> '
    f"Assalomu alaykum, StarPayUz — {display_name}!\n"
    f'<tg-emoji emoji-id="{EMOJI_MONEY}">💰</tg-emoji> '
    f"Balans: {balance:,} so'm\n"
    f'<tg-emoji emoji-id="{EMOJI_PEOPLE}">👥</tg-emoji> '
    f"Referallar: {refs} ta\n\n"
    f'<tg-emoji emoji-id="{EMOJI_LIGHTNING}">⚡️</tg-emoji> '
    f"Quyidagilardan kerakli bo'limni tanlang:"
  )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
  tg = message.from_user
  if not tg:
    return

  ref_id = None
  if message.text and len(message.text.split()) > 1:
    arg = message.text.split(maxsplit=1)[1]
    if arg.isdigit():
      ref_id = int(arg)

  user = await ensure_user(tg.id, tg.username, tg.full_name, referred_by=ref_id)
  name = tg.full_name or tg.username or "Foydalanuvchi"

  await message.answer(
    menu_text(user, name),
    reply_markup=main_inline_keyboard(),
  )
  await message.answer(
    "📋 Pastki menyu:",
    reply_markup=bottom_reply_keyboard(),
  )


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
  tg = message.from_user
  if not tg:
    return
  user = await get_user(tg.id) or await ensure_user(
    tg.id, tg.username, tg.full_name
  )
  name = tg.full_name or tg.username or "Foydalanuvchi"
  await message.answer(
    menu_text(user, name),
    reply_markup=main_inline_keyboard(),
  )
