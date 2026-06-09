from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.keyboards import bottom_reply_keyboard, main_inline_keyboard
from services.database import ensure_user, get_user

router = Router()

EMOJI_WAVE = "5312345830382910731"  # 👋
EMOJI_ORANGE = "5336936725765700868"  # 🟠
EMOJI_WALLET = "5215420556089776398"  # 👛
EMOJI_PEOPLE = "5879905000972358125"  # 👥
EMOJI_LIGHTNING = "5224496844188458905"  # ⚡️


def menu_text(
  user: dict,
  username: str | None,
  first_name: str | None,
) -> str:
  balance = user.get("balance", 0)
  refs = user.get("referrals", 0)
  sp_id = user.get("sp_id") or user.get("id") or user.get("telegram_id", "—")
  display = f"@{username}" if username else (first_name or "Foydalanuvchi")
  return (
    f'<tg-emoji emoji-id="{EMOJI_WAVE}">👋</tg-emoji> '
    f"<b>Assalomu alaykum, {display}</b>\n\n"
    f'<tg-emoji emoji-id="{EMOJI_ORANGE}">🟠</tg-emoji> '
    f"<b>StarPayUz ID:</b> <code>{sp_id}</code>\n"
    f"┗ <tg-emoji emoji-id=\"{EMOJI_WALLET}\">👛</tg-emoji> "
    f"<b>Balans:</b> {balance:,} so'm\n"
    f"┗ <tg-emoji emoji-id=\"{EMOJI_PEOPLE}\">👥</tg-emoji> "
    f"<b>Referallar:</b> {refs} ta\n\n"
    f"<blockquote>"
    f'<tg-emoji emoji-id="{EMOJI_LIGHTNING}">⚡️</tg-emoji> '
    f"<b>Kerakli bo'limni tanlang:</b>"
    f"</blockquote>"
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

  await message.answer(
    menu_text(user, tg.username, tg.first_name),
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
  await message.answer(
    menu_text(user, tg.username, tg.first_name),
    reply_markup=main_inline_keyboard(),
  )
