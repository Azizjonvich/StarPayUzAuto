from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import config
from services.database import db

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in config.ADMINS


@router.message(Command("admin_check"))
async def cmd_admin_check(message: Message) -> None:
    """Debug command to check if user is admin"""
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    is_admin = _is_admin(user_id)
    
    await message.answer(
        f"🔍 <b>Admin Check</b>\n\n"
        f"Your Telegram ID: <code>{user_id}</code>\n"
        f"Admin list: <code>{config.ADMINS}</code>\n"
        f"Is admin: {'✅ YES' if is_admin else '❌ NO'}",
        parse_mode="HTML",
    )


@router.message(Command("user"))
async def cmd_user_info(message: Message) -> None:
    if not message.from_user:
        return
    
    if not _is_admin(message.from_user.id):
        await message.answer("❌ Bu buyruq faqat adminlar uchun.")
        return

    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer(
            "Foydalanish: <code>/user 12</code>\n"
            "StarPayUz ID bo'yicha foydalanuvchini ko'rsatadi.",
            parse_mode="HTML",
        )
        return

    user = await db.get_user_by_sp_id(int(parts[1]))
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi.")
        return

    username = f"@{user['username']}" if user.get("username") else "—"
    await message.answer(
        f"👤 <b>Foydalanuvchi #{user['sp_id']}</b>\n\n"
        f"StarPayUz ID: <code>{user['sp_id']}</code>\n"
        f"Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"Username: {username}\n"
        f"Ism: {user.get('full_name') or '—'}\n"
        f"Balans: <b>{user['balance']:,.0f}</b> so'm\n"
        f"Referallar: {user.get('referrals', 0)} ta",
        parse_mode="HTML",
    )


@router.message(Command("bal"))
async def cmd_balance(message: Message) -> None:
    if not message.from_user:
        return
        
    if not _is_admin(message.from_user.id):
        await message.answer("❌ Bu buyruq faqat adminlar uchun.")
        return

    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer(
            "Foydalanish:\n"
            "<code>/bal 12 +50000</code> — balans qo'shish\n"
            "<code>/bal 12 -10000</code> — balans ayirish\n"
            "<code>/user 12</code> — foydalanuvchi ma'lumoti\n\n"
            "ID — bu foydalanuvchining <b>StarPayUz ID</b> si (Telegram ID emas).",
            parse_mode="HTML",
        )
        return

    if not parts[1].isdigit():
        await message.answer("❌ StarPayUz ID raqam bo'lishi kerak.")
        return

    sp_id = int(parts[1])
    raw_amount = parts[2]
    if raw_amount.startswith("+"):
        operation = "add"
        amount_text = raw_amount[1:]
    elif raw_amount.startswith("-"):
        operation = "subtract"
        amount_text = raw_amount[1:]
    else:
        await message.answer("❌ Summa + yoki - bilan boshlanishi kerak.")
        return

    try:
        amount = float(amount_text.replace(",", "").replace(" ", ""))
    except ValueError:
        await message.answer("❌ Noto'g'ri summa.")
        return

    if amount <= 0:
        await message.answer("❌ Summa 0 dan katta bo'lishi kerak.")
        return

    user = await db.update_balance_by_sp_id(sp_id, int(amount), operation)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi.")
        return

    action = "qo'shildi" if operation == "add" else "ayirildi"
    await message.answer(
        f"✅ <b>{amount:,.0f}</b> so'm {action}\n\n"
        f"Foydalanuvchi: <code>#{user['sp_id']}</code>\n"
        f"Yangi balans: <b>{user['balance']:,.0f}</b> so'm",
        parse_mode="HTML",
    )
