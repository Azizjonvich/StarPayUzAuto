"""Admin panel — внутри бота (inline меню, без веба)"""
import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import config
import keyboards
from services.database import (
    add_balance, add_balance_history, deduct_balance, db,
    get_all_users_telegram_ids, get_dashboard_stats, get_order_by_id,
    get_orders_paginated, get_users_paginated, search_users_db,
    block_user_db, unblock_user_db, delete_user_db,
    update_order_status,
)

logger = logging.getLogger(__name__)
router = Router()


# ─── States ───────────────────────────────────────────────────────

class AdminStates(StatesGroup):
    broadcast_text = State()
    balance_sp_id = State()
    balance_amount = State()
    balance_reason = State()
    balance_action = State()
    search_query = State()
    order_status = State()
    settings_key = State()
    settings_value = State()


# ─── Helper ───────────────────────────────────────────────────────

def _is_admin(user_id: int) -> bool:
    return user_id in config.ADMINS


async def _deny(message: Message):
    await message.answer("❌ <b>Bu buyruq faqat administratorlar uchun.</b>")


# ─── /admin — вход в админ-панель ────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext = None):
    if not message.from_user:
        return
    if not _is_admin(message.from_user.id):
        await _deny(message)
        return
    if state:
        await state.clear()
    await message.answer(
        "🔐 <b>Admin Panel</b>\n\nXush kelibsiz, administrator!",
        reply_markup=keyboards.get_admin_main_keyboard()
    )


# ─── Главное меню админки ────────────────────────────────────────

@router.callback_query(F.data == "admin_main_menu")
async def admin_main_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🔐 <b>Admin Panel</b>\n\nBo'limni tanlang:",
        reply_markup=keyboards.get_admin_main_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# 1. СТАТИСТИКА / DASHBOARD
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    await callback.answer("⏳ Yuklanmoqda...")
    try:
        stats = await get_dashboard_stats()
        text = (
            "📊 <b>Dashboard statistika</b>\n\n"
            f"👥 <b>Foydalanuvchilar:</b> {stats['total_users']:,}\n"
            f"┣ Yangi (bugun): {stats['new_today']:,}\n"
            f"┣ Yangi (7 kun): {stats['new_week']:,}\n"
            f"┗ Yangi (30 kun): {stats['new_month']:,}\n\n"
            f"💰 <b>Umumiy balans:</b> {stats['total_balance']:,} so'm\n"
            f"📦 <b>Buyurtmalar:</b> {stats['total_orders']:,}\n"
        )
    except Exception as e:
        logger.error(f"Stats error: {e}")
        text = "❌ Statistikani yuklashda xatolik."

    await callback.message.edit_text(text, reply_markup=keyboards.get_admin_back_keyboard())


# ═══════════════════════════════════════════════════════════════════
# 2. ПОЛЬЗОВАТЕЛИ
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin_users")
async def admin_users_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "👥 <b>Foydalanuvchilar</b>\n\n"
        "Foydalanuvchilarni boshqarish:",
        reply_markup=keyboards.get_admin_users_keyboard(),
    )


@router.callback_query(F.data == "admin_users_list_skip")
async def admin_users_list_skip(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("admin_users_list_"))
async def admin_users_list(callback: CallbackQuery):
    await callback.answer()
    page = int(callback.data.split("_")[-1])
    try:
        users, total = await get_users_paginated(page=page, page_size=10)
        text = f"👥 <b>Foydalanuvchilar</b> (jami: {total:,})\n\n"
        for u in users:
            name = u.get("username") or u.get("full_name") or "—"
            blocked = " 🔒" if u.get("is_blocked") else ""
            text += (
                f"• <code>{u['sp_id']}</code> "
                f"<b>{name}</b>{blocked}\n"
                f"  Balans: {u['balance']:,} so'm\n"
            )
    except Exception as e:
        logger.error(f"Users list error: {e}")
        text = "❌ Xatolik yuz berdi."

    kb = keyboards.get_admin_users_list_keyboard(page, total > page * 10)
    await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "admin_users_search")
async def admin_users_search_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "🔍 <b>Foydalanuvchini qidirish</b>\n\n"
        "Telegram ID, username yoki SP ID ni kiriting:"
    )
    await state.set_state(AdminStates.search_query)


@router.message(AdminStates.search_query)
async def admin_users_search_result(message: Message, state: FSMContext):
    query = message.text.strip()
    try:
        users = await search_users_db(query)
        if not users:
            await message.answer("❌ Foydalanuvchi topilmadi.")
        else:
            for u in users[:5]:
                name = u.get("username") or u.get("full_name") or "—"
                blocked = " 🔒" if u.get("is_blocked") else ""
                text = (
                    f"👤 <b>#{u['sp_id']}</b>{blocked}\n"
                    f"Telegram ID: <code>{u['telegram_id']}</code>\n"
                    f"Ism: {name}\n"
                    f"Balans: <b>{u['balance']:,}</b> so'm\n"
                    f"Referallar: {u.get('referrals', 0)} ta\n"
                )
                await message.answer(
                    text,
                    reply_markup=keyboards.get_admin_user_actions_keyboard(u['telegram_id']),
                )
    except Exception as e:
        logger.error(f"Search error: {e}")
        await message.answer("❌ Xatolik yuz berdi.")
    await state.clear()
    await message.answer(
        "🔐 Admin Panel", reply_markup=keyboards.get_admin_main_keyboard()
    )


# ─── Блокировка / Разблокировка / Удаление ───────────────────────

@router.callback_query(F.data.startswith("admin_user_block_"))
async def admin_user_block(callback: CallbackQuery):
    await callback.answer()
    tid = int(callback.data.split("_")[-1])
    try:
        await block_user_db(tid)
        await callback.message.edit_text(f"✅ Foydalanuvchi <code>{tid}</code> bloklandi.")
    except Exception as e:
        await callback.message.edit_text(f"❌ Xatolik: {e}")


@router.callback_query(F.data.startswith("admin_user_unblock_"))
async def admin_user_unblock(callback: CallbackQuery):
    await callback.answer()
    tid = int(callback.data.split("_")[-1])
    try:
        await unblock_user_db(tid)
        await callback.message.edit_text(f"✅ Foydalanuvchi <code>{tid}</code> blokdan chiqarildi.")
    except Exception as e:
        await callback.message.edit_text(f"❌ Xatolik: {e}")


@router.callback_query(F.data.startswith("admin_user_delete_"))
async def admin_user_delete(callback: CallbackQuery):
    await callback.answer()
    tid = int(callback.data.split("_")[-1])
    try:
        await delete_user_db(tid)
        await callback.message.edit_text(f"🗑 Foydalanuvchi <code>{tid}</code> o'chirildi.")
    except Exception as e:
        await callback.message.edit_text(f"❌ Xatolik: {e}")


# ═══════════════════════════════════════════════════════════════════
# 3. БАЛАНС
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin_balance")
async def admin_balance_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "💰 <b>Balans boshqaruvi</b>\n\n"
        "Foydalanuvchi SP ID sini kiriting:"
    )
    await state.set_state(AdminStates.balance_sp_id)


@router.message(AdminStates.balance_sp_id)
async def admin_balance_sp_id_received(message: Message, state: FSMContext):
    if not message.text or not message.text.strip().isdigit():
        await message.answer("❌ SP ID raqam bo'lishi kerak. Qayta kiriting yoki /admin ni bosing.")
        return
    sp_id = int(message.text.strip())
    user = await db.get_user_by_sp_id(sp_id)
    if not user:
        await message.answer(f"❌ SP ID <code>{sp_id}</code> bo'yicha foydalanuvchi topilmadi.")
        return
    await state.update_data(balance_sp_id=sp_id, balance_user_tid=user["telegram_id"], balance_current=user["balance"])
    await message.answer(
        f"👤 <b>Foydalanuvchi #{sp_id}</b>\n"
        f"Balans: <b>{user['balance']:,}</b> so'm\n\n"
        "Amalni tanlang:",
        reply_markup=keyboards.get_admin_balance_actions_keyboard(),
    )
    await state.set_state(AdminStates.balance_action)


@router.callback_query(F.data.startswith("admin_balance_act_"), AdminStates.balance_action)
async def admin_balance_action(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    action = callback.data.split("_")[-1]
    await state.update_data(balance_action=action)
    action_label = "qo'shish" if action == "add" else "ayirish"
    await callback.message.edit_text(
        f"💰 <b>Balans {action_label}</b>\n\n"
        "Summani kiriting (so'mda):"
    )
    await state.set_state(AdminStates.balance_amount)


@router.message(AdminStates.balance_amount)
async def admin_balance_amount_received(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip().replace(",", "").replace(" ", ""))
    except ValueError:
        await message.answer("❌ Noto'g'ri summa. Raqam kiriting.")
        return
    if amount <= 0:
        await message.answer("❌ Summa 0 dan katta bo'lishi kerak.")
        return
    await state.update_data(balance_amount=amount)
    await message.answer("📝 Sababni kiriting (yoki '-' ni yuboring):")
    await state.set_state(AdminStates.balance_reason)


@router.message(AdminStates.balance_reason)
async def admin_balance_reason_received(message: Message, state: FSMContext):
    reason = message.text.strip() if message.text and message.text.strip() != "-" else None
    data = await state.get_data()
    action = data["balance_action"]
    amount = data["balance_amount"]
    tid = data["balance_user_tid"]
    old_balance = data["balance_current"]

    try:
        if action == "add":
            new_balance = await add_balance(tid, amount)
            tx_type = "credit"
        else:
            ok = await deduct_balance(tid, amount)
            if not ok:
                await message.answer("❌ Balans yetarli emas!")
                await state.clear()
                return
            user = await db.get_user(tid)
            new_balance = user["balance"] if user else old_balance
            tx_type = "debit"

        await add_balance_history(tid, amount, tx_type, old_balance, new_balance, reason)
        user = await db.get_user(tid)
        sp_id = user["sp_id"] if user else "?"
        action_text = "Qo'shish" if action == "add" else "Ayirish"
        await message.answer(
            f"✅ <b>Balans o'zgartirildi</b>\n\n"
            f"Foydalanuvchi: <code>#{sp_id}</code>\n"
            f"Amal: {action_text}\n"
            f"Summa: {amount:,} so'm\n"
            f"Oldingi balans: {old_balance:,} so'm\n"
            f"Yangi balans: <b>{new_balance:,}</b> so'm\n"
            f"Sabab: {reason or '—'}"
        )
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

    await state.clear()
    await message.answer("🔐 Admin Panel", reply_markup=keyboards.get_admin_main_keyboard())


# ═══════════════════════════════════════════════════════════════════
# 4. РАССЫЛКА
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "📢 <b>Xabar yuborish</b>\n\n"
        "Yubormoqchi bo'lgan xabaringizni kiriting\n"
        "(matn, rasm, video — istalgan formatda):"
    )
    await state.set_state(AdminStates.broadcast_text)


@router.message(AdminStates.broadcast_text)
async def admin_broadcast_preview(message: Message, state: FSMContext):
    # Use copyMessage for broadcast — preserves ALL formatting including premium emoji
    await state.update_data(
        broadcast_msg_id=message.message_id,
        broadcast_chat_id=message.chat.id,
    )

    # Copy the admin's message back as preview (exact copy with all formatting)
    await message.bot.copy_message(
        chat_id=message.chat.id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )

    # Confirm buttons
    await message.answer(
        "📢 <b>Yuqoridagi xabarni yuborish?</b>",
        parse_mode="HTML",
        reply_markup=keyboards.get_admin_broadcast_confirm_keyboard(),
    )


@router.callback_query(F.data == "admin_broadcast_confirm")
async def admin_broadcast_confirm_cb(callback: CallbackQuery, state: FSMContext):
    await callback.answer("⏳ Yuborilmoqda...")
    data = await state.get_data()
    msg_id = data.get("broadcast_msg_id")
    chat_id = data.get("broadcast_chat_id")

    if not msg_id or not chat_id:
        await callback.message.edit_text("❌ Xabar topilmadi. Qaytadan urinib ko'ring.")
        return

    await callback.message.edit_text("⏳ Xabar yuborilmoqda, biroz kuting...")
    try:
        tgs = await get_all_users_telegram_ids()
        sent = 0
        for tid in tgs:
            try:
                # CopyMessage preserves ALL formatting: premium emoji, bold, inline entities, etc.
                await callback.bot.copy_message(
                    chat_id=tid,
                    from_chat_id=chat_id,
                    message_id=msg_id,
                )
                sent += 1
            except Exception as exc:
                logger.warning(f"Broadcast copy failed to {tid}: {exc}")
            await asyncio.sleep(0.05)
        await callback.message.answer(f"✅ Xabar {sent}/{len(tgs)} foydalanuvchiga yuborildi.")
    except Exception as e:
        await callback.message.answer(f"❌ Xatolik: {e}")
    await state.clear()
    await callback.message.answer("🔐 Admin Panel", reply_markup=keyboards.get_admin_main_keyboard())


@router.callback_query(F.data == "admin_broadcast_cancel")
async def admin_broadcast_cancel_cb(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ Xabar yuborish bekor qilindi.")
    await callback.message.answer("🔐 Admin Panel", reply_markup=keyboards.get_admin_main_keyboard())


# ═══════════════════════════════════════════════════════════════════
# 5. ЗАКАЗЫ
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin_orders_skip")
async def admin_orders_skip(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "admin_orders")
async def admin_orders_menu(callback: CallbackQuery):
    await callback.answer()
    page = 1
    try:
        orders, total = await get_orders_paginated(page=page, page_size=5)
        text = f"📦 <b>Buyurtmalar</b> (jami: {total:,})\n\n"
    except Exception:
        orders = []
        total = 0
        text = "📦 <b>Buyurtmalar</b>\n\nMa'lumot topilmadi."

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_orders_keyboard(orders, page, total),
    )


@router.callback_query(F.data.startswith("admin_orders_page_"))
async def admin_orders_page(callback: CallbackQuery):
    await callback.answer()
    page = int(callback.data.split("_")[-1])
    try:
        orders, total = await get_orders_paginated(page=page, page_size=5)
        text = f"📦 <b>Buyurtmalar</b> (jami: {total:,})\n\n"
    except Exception:
        orders = []
        total = 0
        text = "📦 <b>Buyurtmalar</b>\n\nMa'lumot topilmadi."

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_orders_keyboard(orders, page, total),
    )


@router.callback_query(F.data.startswith("admin_order_status_"))
async def admin_order_status_change(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    oid = int(parts[3])
    new_status = parts[4]
    try:
        await update_order_status(oid, new_status)
        await callback.message.edit_text(f"✅ Buyurtma #{oid} holati o'zgartirildi: {new_status}")
    except Exception as e:
        await callback.message.edit_text(f"❌ Xatolik: {e}")


@router.callback_query(F.data.startswith("admin_order_detail_"))
async def admin_order_detail(callback: CallbackQuery):
    await callback.answer()
    oid = int(callback.data.split("_")[-1])
    try:
        o = await get_order_by_id(oid)
        if o:
            text = (
                f"📦 <b>Buyurtma #{o['id']}</b>\n\n"
                f"Telegram ID: <code>{o['telegram_id']}</code>\n"
                f"Mahsulot: {o.get('product_type', '?')}\n"
                f"Miqdor: {o.get('quantity', '—')}\n"
                f"Summa: {o.get('amount', 0):,} so'm\n"
                f"Holat: {o['status']}\n"
                f"Yaratilgan: {o.get('created_at', '—')}\n"
            )
            await callback.message.edit_text(
                text,
                reply_markup=keyboards.get_admin_order_detail_keyboard(oid, o["status"]),
            )
        else:
            await callback.message.edit_text("❌ Buyurtma topilmadi.")
    except Exception as e:
        await callback.message.edit_text(f"❌ Xatolik: {e}")


# ═══════════════════════════════════════════════════════════════════
# 6. НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════════════

# Настройки хранятся в памяти (можно сохранить в БД позже)
_runtime_settings = {
    "stars_price_per_unit": 200,        # Цена за 1 star (сум)
    "min_topup_amount": 1000,           # Минимальное пополнение
    "max_topup_amount": 100_000_000,    # Максимальное пополнение
    "referral_bonus": 300,              # Бонус за реферала
    "gift_enabled": True,               # Включить/выключить подарки
    "stars_enabled": True,              # Включить/выключить Stars
    "maintenance_mode": False,          # Режим обслуживания
}

SETTINGS_LABELS = {
    "stars_price_per_unit": "⭐ Stars narxi (so'm/1 star)",
    "min_topup_amount": "💳 Min to'ldirish (so'm)",
    "max_topup_amount": "💳 Max to'ldirish (so'm)",
    "referral_bonus": "👥 Referal bonusi (so'm)",
    "gift_enabled": "🎁 Sovg'alar (true/false)",
    "stars_enabled": "⭐ Stars xizmati (true/false)",
    "maintenance_mode": "🔧 Texnik ishlar rejimi (true/false)",
}


def _settings_text() -> str:
    lines = ["⚙️ <b>Sozlamalar</b>\n"]
    for key, label in SETTINGS_LABELS.items():
        val = _runtime_settings.get(key)
        lines.append(f"• {label}\n  <code>{key}</code> = <b>{val}</b>")
    lines.append("\n✏️ O'zgartirish uchun kalit nomini yuboring")
    return "\n".join(lines)


def _settings_keyboard():
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for key in SETTINGS_LABELS:
        builder.row(InlineKeyboardButton(
            text=f"✏️ {SETTINGS_LABELS[key].split('(')[0].strip()}",
            callback_data=f"admin_set_{key}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_main_menu"))
    return builder.as_markup()


@router.callback_query(F.data == "admin_settings")
async def admin_settings_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        _settings_text(),
        reply_markup=_settings_keyboard(),
    )


@router.callback_query(F.data.startswith("admin_set_"))
async def admin_set_key(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    key = callback.data[len("admin_set_"):]
    if key not in _runtime_settings:
        await callback.answer("❌ Noma'lum kalit", show_alert=True)
        return
    current = _runtime_settings[key]
    label = SETTINGS_LABELS.get(key, key)
    await callback.message.edit_text(
        f"✏️ <b>{label}</b>\n\n"
        f"Hozirgi qiymat: <code>{current}</code>\n\n"
        f"Yangi qiymatni kiriting:\n"
        f"<i>(raqam yoki true/false)</i>"
    )
    await state.update_data(settings_key=key)
    await state.set_state(AdminStates.settings_value)


@router.message(AdminStates.settings_value)
async def admin_set_value(message: Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("settings_key")
    raw = (message.text or "").strip()

    if key not in _runtime_settings:
        await message.answer("❌ Xatolik. Qaytadan /admin")
        await state.clear()
        return

    current = _runtime_settings[key]
    # Определяем тип по текущему значению
    try:
        if isinstance(current, bool):
            if raw.lower() in ("true", "1", "ha", "yes"):
                new_val = True
            elif raw.lower() in ("false", "0", "yoq", "no"):
                new_val = False
            else:
                raise ValueError("bool kerak: true yoki false")
        elif isinstance(current, int):
            new_val = int(raw.replace(",", "").replace(" ", ""))
        elif isinstance(current, float):
            new_val = float(raw)
        else:
            new_val = raw
    except ValueError as e:
        await message.answer(f"❌ Noto'g'ri qiymat: {e}\nQayta kiriting:")
        return

    _runtime_settings[key] = new_val
    label = SETTINGS_LABELS.get(key, key)
    logger.info(f"Admin {message.from_user.id} changed setting {key}: {current} → {new_val}")

    await message.answer(
        f"✅ <b>Sozlama yangilandi</b>\n\n"
        f"{label}\n"
        f"Eski: <code>{current}</code>\n"
        f"Yangi: <b><code>{new_val}</code></b>",
    )
    await state.clear()
    await message.answer(
        _settings_text(),
        reply_markup=_settings_keyboard(),
    )


def get_setting(key: str):
    """Get runtime setting value — use in API/handlers"""
    return _runtime_settings.get(key)
