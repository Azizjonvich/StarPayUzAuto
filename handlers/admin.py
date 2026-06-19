import asyncio
import logging
import time

from aiogram import F, Bot, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import config
import keyboards.admin as admin_kb
from services.database import (
    add_balance, add_balance_history, deduct_balance, db,
    get_all_users_telegram_ids, get_dashboard_stats, get_order_by_id,
    get_orders_paginated, get_users_paginated, search_users_db,
    block_user_db, unblock_user_db, delete_user_db,
    update_order_status, record_payment, get_pool,
)

logger = logging.getLogger(__name__)
router = Router()


class AdminStates(StatesGroup):
    broadcast_text = State()
    balance_sp_id = State()
    balance_amount = State()
    balance_reason = State()
    balance_action = State()
    search_query = State()
    settings_key = State()
    settings_value = State()


def _is_admin(user_id: int) -> bool:
    return user_id in config.ADMINS


async def _deny(message: Message):
    await message.answer("❌ <b>Bu buyruq faqat administratorlar uchun.</b>")


async def _get_ping(bot: Bot) -> int:
    start = time.monotonic()
    await bot.get_me()
    return int((time.monotonic() - start) * 1000)


async def _admin_header(bot: Bot) -> str:
    ping = await _get_ping(bot)
    return (
        "\u2699\ufe0f <b>\u0410\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440 \u043f\u0430\u043d\u0435\u043b\u0438</b>\n\n"
        f"\U0001f4a1 PING: {ping} MS\n\n"
        "\u0412\u044b \u0438\u043c\u0435\u0435\u0442\u0435 \u043f\u0440\u0430\u0432\u0430 \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u0430.\n"
        "\u041f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u0440\u0430\u0431\u043e\u0442\u0430\u0439\u0442\u0435 \u043e\u0441\u0442\u043e\u0440\u043e\u0436\u043d\u043e."
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext = None):
    if not message.from_user:
        return
    if not _is_admin(message.from_user.id):
        await _deny(message)
        return
    if state:
        await state.clear()
    header = await _admin_header(message.bot)
    await message.answer(header, reply_markup=admin_kb.admin_main_keyboard())


@router.callback_query(F.data == "admin_main_menu")
async def admin_main_menu_cb(callback: CallbackQuery, state: FSMContext = None):
    await callback.answer()
    if state:
        await state.clear()
    header = await _admin_header(callback.bot)
    await callback.message.edit_text(header, reply_markup=admin_kb.admin_main_keyboard())


@router.callback_query(F.data == "admin_stats")
async def admin_stats_cb(callback: CallbackQuery):
    await callback.answer("\u23f3 \u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430...")
    try:
        stats = await get_dashboard_stats()
        pool = await get_pool()
        async with pool.acquire() as conn:
            payments_count = await conn.fetchval("SELECT COUNT(*) FROM payments") or 0
            total_profit = await conn.fetchval(
                "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'paid'"
            ) or 0
        text = (
            f"\U0001f4ca <b>\u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430</b>\n\n"
            f"\U0001f465 <b>\u0412\u0441\u0435\u0433\u043e \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u0435\u0439:</b> {stats['total_users']:,}\n"
            f"\U0001f4c5 \u0417\u0430 \u0441\u0435\u0433\u043e\u0434\u043d\u044f: {stats['new_today']:,}\n"
            f"\U0001f4c5 \u0417\u0430 \u043d\u0435\u0434\u0435\u043b\u044e: {stats['new_week']:,}\n\n"
            f"\U0001f4b3 <b>\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u043f\u043b\u0430\u0442\u0435\u0436\u0435\u0439:</b> {payments_count:,}\n"
            f"\U0001f4b0 <b>\u041e\u0431\u0449\u0430\u044f \u043f\u0440\u0438\u0431\u044b\u043b\u044c:</b> {total_profit:,} \u0441\u0443\u043c"
        )
    except Exception as e:
        logger.error(f"Stats error: {e}")
        text = "\u274c \u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0438 \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0438."
    await callback.message.edit_text(text, reply_markup=admin_kb.stats_keyboard())


@router.callback_query(F.data == "admin_users")
async def admin_users_menu_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "\U0001f534 <b>\u0423\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f\u043c\u0438</b>\n\n\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435:",
        reply_markup=admin_kb.users_main_keyboard(),
    )


@router.callback_query(F.data.startswith("admin_users_list_"))
async def admin_users_list_cb(callback: CallbackQuery):
    await callback.answer()
    data = callback.data
    if data == "admin_users_list_skip":
        return
    page = int(data.split("_")[-1])
    try:
        users, total = await get_users_paginated(page=page, page_size=10)
        text = f"\U0001f465 <b>\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u0438</b> (\u0432\u0441\u0435\u0433\u043e: {total:,})\n\n"
        for u in users:
            name = u.get("username") or u.get("full_name") or "\u2014"
            blocked = " \U0001f512" if u.get("is_blocked") else ""
            text += (
                f"\u2022 <code>{u['sp_id']}</code> "
                f"<b>{name}</b>{blocked}\n"
                f"  \u0411\u0430\u043b\u0430\u043d\u0441: {u['balance']:,} \u0441\u0443\u043c\n"
            )
    except Exception as e:
        logger.error(f"Users list error: {e}")
        text = "\u274c \u041e\u0448\u0438\u0431\u043a\u0430."
    kb = admin_kb.users_list_keyboard(page, total > page * 10)
    await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "admin_users_search")
async def admin_users_search_start_cb(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "\U0001f50d <b>\u041f\u043e\u0438\u0441\u043a \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f</b>\n\n"
        "\u0412\u0432\u0435\u0434\u0438\u0442\u0435 Telegram ID, \u0438\u043c\u044f \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f \u0438\u043b\u0438 SP ID:"
    )
    await state.set_state(AdminStates.search_query)


@router.message(AdminStates.search_query)
async def admin_users_search_result_msg(message: Message, state: FSMContext):
    query = message.text.strip()
    try:
        users = await search_users_db(query)
        if not users:
            await message.answer("\u274c \u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d.")
        else:
            for u in users[:5]:
                name = u.get("username") or u.get("full_name") or "\u2014"
                blocked = " \U0001f512" if u.get("is_blocked") else ""
                text = (
                    f"\U0001f464 <b>#{u['sp_id']}</b>{blocked}\n"
                    f"Telegram ID: <code>{u['telegram_id']}</code>\n"
                    f"\u0418\u043c\u044f: {name}\n"
                    f"\u0411\u0430\u043b\u0430\u043d\u0441: <b>{u['balance']:,}</b> \u0441\u0443\u043c\n"
                    f"\u0420\u0435\u0444\u0435\u0440\u0430\u043b\u044b: {u.get('referrals', 0)}"
                )
                await message.answer(
                    text,
                    reply_markup=admin_kb.user_actions_keyboard(u['telegram_id']),
                )
    except Exception as e:
        logger.error(f"Search error: {e}")
        await message.answer("\u274c \u041e\u0448\u0438\u0431\u043a\u0430.")
    await state.clear()
    header = await _admin_header(message.bot)
    await message.answer(header, reply_markup=admin_kb.admin_main_keyboard())


@router.callback_query(F.data.startswith("admin_user_block_"))
async def admin_user_block_cb(callback: CallbackQuery):
    await callback.answer()
    tid = int(callback.data.split("_")[-1])
    try:
        await block_user_db(tid)
        await callback.message.edit_text(f"\u2705 \u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c <code>{tid}</code> \u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043d.")
    except Exception as e:
        await callback.message.edit_text(f"\u274c \u041e\u0448\u0438\u0431\u043a\u0430: {e}")


@router.callback_query(F.data.startswith("admin_user_unblock_"))
async def admin_user_unblock_cb(callback: CallbackQuery):
    await callback.answer()
    tid = int(callback.data.split("_")[-1])
    try:
        await unblock_user_db(tid)
        await callback.message.edit_text(f"\u2705 \u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c <code>{tid}</code> \u0440\u0430\u0437\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043d.")
    except Exception as e:
        await callback.message.edit_text(f"\u274c \u041e\u0448\u0438\u0431\u043a\u0430: {e}")


@router.callback_query(F.data.startswith("admin_user_delete_"))
async def admin_user_delete_cb(callback: CallbackQuery):
    await callback.answer()
    tid = int(callback.data.split("_")[-1])
    try:
        await delete_user_db(tid)
        await callback.message.edit_text(f"\U0001f5d1 \u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c <code>{tid}</code> \u0443\u0434\u0430\u043b\u0451\u043d.")
    except Exception as e:
        await callback.message.edit_text(f"\u274c \u041e\u0448\u0438\u0431\u043a\u0430: {e}")


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start_cb(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "\U0001f4e8 <b>\u0420\u0430\u0441\u0441\u044b\u043b\u043a\u0430</b>\n\n"
        "\u041e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435, \u043a\u043e\u0442\u043e\u0440\u043e\u0435 \u0445\u043e\u0442\u0438\u0442\u0435 \u0440\u0430\u0437\u043e\u0441\u043b\u0430\u0442\u044c \u0432\u0441\u0435\u043c \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f\u043c\n"
        "(\u0442\u0435\u043a\u0441\u0442, \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435, \u0432\u0438\u0434\u0435\u043e \u2014 \u043b\u044e\u0431\u043e\u0439 \u0444\u043e\u0440\u043c\u0430\u0442):"
    )
    await state.set_state(AdminStates.broadcast_text)


@router.message(AdminStates.broadcast_text)
async def admin_broadcast_preview_msg(message: Message, state: FSMContext):
    await state.update_data(
        broadcast_msg_id=message.message_id,
        broadcast_chat_id=message.chat.id,
    )
    await message.bot.copy_message(
        chat_id=message.chat.id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    await message.answer(
        "\U0001f4e8 <b>\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u044d\u0442\u043e \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435?</b>",
        reply_markup=admin_kb.broadcast_confirm_keyboard(),
    )


@router.callback_query(F.data == "admin_broadcast_confirm")
async def admin_broadcast_confirm_cb(callback: CallbackQuery, state: FSMContext):
    await callback.answer("\u23f3 \u041e\u0442\u043f\u0440\u0430\u0432\u043b\u044f\u0435\u0442\u0441\u044f...")
    data = await state.get_data()
    msg_id = data.get("broadcast_msg_id")
    chat_id = data.get("broadcast_chat_id")
    if not msg_id or not chat_id:
        await callback.message.edit_text("\u274c \u0421\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e.")
        return
    await callback.message.edit_text("\u23f3 \u0420\u0430\u0441\u0441\u044b\u043b\u043a\u0430 \u0432\u044b\u043f\u043e\u043b\u043d\u044f\u0435\u0442\u0441\u044f...")
    try:
        tgs = await get_all_users_telegram_ids()
        sent = 0
        for tid in tgs:
            try:
                await callback.bot.copy_message(
                    chat_id=tid,
                    from_chat_id=chat_id,
                    message_id=msg_id,
                )
                sent += 1
            except Exception as exc:
                logger.warning(f"Broadcast failed to {tid}: {exc}")
            await asyncio.sleep(0.05)
        await callback.message.answer(f"\u2705 \u0420\u0430\u0441\u0441\u044b\u043b\u043a\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430. \u041e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u043e: {sent}/{len(tgs)}")
    except Exception as e:
        await callback.message.answer(f"\u274c \u041e\u0448\u0438\u0431\u043a\u0430: {e}")
    await state.clear()
    header = await _admin_header(callback.bot)
    await callback.message.answer(header, reply_markup=admin_kb.admin_main_keyboard())


@router.callback_query(F.data == "admin_broadcast_cancel")
async def admin_broadcast_cancel_cb(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("\u274c \u0420\u0430\u0441\u0441\u044b\u043b\u043a\u0430 \u043e\u0442\u043c\u0435\u043d\u0435\u043d\u0430.")
    header = await _admin_header(callback.bot)
    await callback.message.answer(header, reply_markup=admin_kb.admin_main_keyboard())


_runtime_settings = {
    "stars_price_per_unit": 200,
    "min_topup_amount": 1000,
    "max_topup_amount": 100_000_000,
    "referral_bonus": 300,
    "gift_enabled": True,
    "stars_enabled": True,
    "maintenance_mode": False,
}

SETTINGS_LABELS = {
    "stars_price_per_unit": "\u2b50 Stars \u0446\u0435\u043d\u0430 (\u0441\u0443\u043c/1 star)",
    "min_topup_amount": "\U0001f4b3 \u041c\u0438\u043d. \u043f\u043e\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u0435 (\u0441\u0443\u043c)",
    "max_topup_amount": "\U0001f4b3 \u041c\u0430\u043a\u0441. \u043f\u043e\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u0435 (\u0441\u0443\u043c)",
    "referral_bonus": "\U0001f465 \u0420\u0435\u0444\u0435\u0440\u0430\u043b\u044c\u043d\u044b\u0439 \u0431\u043e\u043d\u0443\u0441 (\u0441\u0443\u043c)",
    "gift_enabled": "\U0001f381 \u041f\u043e\u0434\u0430\u0440\u043a\u0438 (true/false)",
    "stars_enabled": "\u2b50 Stars \u0441\u0435\u0440\u0432\u0438\u0441 (true/false)",
    "maintenance_mode": "\U0001f6a7 \u0420\u0435\u0436\u0438\u043c \u043e\u0431\u0441\u043b\u0443\u0436\u0438\u0432\u0430\u043d\u0438\u044f (true/false)",
}


def _settings_text() -> str:
    lines = ["\u2699\ufe0f <b>\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438</b>\n"]
    for key, label in SETTINGS_LABELS.items():
        val = _runtime_settings.get(key)
        lines.append(f"\u2022 {label}\n  <code>{key}</code> = <b>{val}</b>")
    lines.append("\n\U0000270f\ufe0f \u041d\u0430\u0436\u043c\u0438\u0442\u0435 \u043d\u0430 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440 \u043d\u0438\u0436\u0435 \u0434\u043b\u044f \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f:")
    return "\n".join(lines)


def _settings_keyboard():
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for key in SETTINGS_LABELS:
        builder.row(InlineKeyboardButton(
            text=f"\u270f\ufe0f {SETTINGS_LABELS[key].split('(')[0].strip()}",
            callback_data=f"admin_set_{key}"
        ))
    builder.row(InlineKeyboardButton(text="\u2b05\ufe0f \u041d\u0430\u0437\u0430\u0434", callback_data="admin_main_menu"))
    return builder.as_markup()


@router.callback_query(F.data == "admin_settings")
async def admin_settings_menu_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        _settings_text(),
        reply_markup=_settings_keyboard(),
    )


@router.callback_query(F.data.startswith("admin_set_"))
async def admin_set_key_cb(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    key = callback.data[len("admin_set_"):]
    if key not in _runtime_settings:
        await callback.answer("\u274c \u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u044b\u0439 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440", show_alert=True)
        return
    current = _runtime_settings[key]
    label = SETTINGS_LABELS.get(key, key)
    await callback.message.edit_text(
        f"\u270f\ufe0f <b>{label}</b>\n\n"
        f"\u0422\u0435\u043a\u0443\u0449\u0435\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435: <code>{current}</code>\n\n"
        f"\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u043d\u043e\u0432\u043e\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435:\n"
        f"<i>(\u0447\u0438\u0441\u043b\u043e \u0438\u043b\u0438 true/false)</i>"
    )
    await state.update_data(settings_key=key)
    await state.set_state(AdminStates.settings_value)


@router.message(AdminStates.settings_value)
async def admin_set_value_msg(message: Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("settings_key")
    raw = (message.text or "").strip()
    if key not in _runtime_settings:
        await message.answer("\u274c \u041e\u0448\u0438\u0431\u043a\u0430. \u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435 /admin")
        await state.clear()
        return
    current = _runtime_settings[key]
    try:
        if isinstance(current, bool):
            if raw.lower() in ("true", "1", "da", "yes"):
                new_val = True
            elif raw.lower() in ("false", "0", "net", "no"):
                new_val = False
            else:
                raise ValueError("\u041d\u0435\u043e\u0431\u0445\u043e\u0434\u0438\u043c\u043e true \u0438\u043b\u0438 false")
        elif isinstance(current, int):
            new_val = int(raw.replace(",", "").replace(" ", ""))
        elif isinstance(current, float):
            new_val = float(raw)
        else:
            new_val = raw
    except ValueError as e:
        await message.answer(f"\u274c \u041d\u0435\u0432\u0435\u0440\u043d\u043e\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435: {e}\n\u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0441\u043d\u043e\u0432\u0430:")
        return
    _runtime_settings[key] = new_val
    label = SETTINGS_LABELS.get(key, key)
    logger.info(f"Admin {message.from_user.id} changed {key}: {current} \u2192 {new_val}")
    await message.answer(
        f"\u2705 <b>\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0430</b>\n\n"
        f"{label}\n"
        f"\u0421\u0442\u0430\u0440\u043e\u0435: <code>{current}</code>\n"
        f"\u041d\u043e\u0432\u043e\u0435: <b><code>{new_val}</code></b>",
    )
    await state.clear()
    await message.answer(
        _settings_text(),
        reply_markup=_settings_keyboard(),
    )


def get_setting(key: str):
    return _runtime_settings.get(key)


@router.callback_query(F.data == "admin_ref_contest")
async def admin_ref_contest_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "\U0001f4e2 <b>\u0420\u0435\u0444\u0435\u0440\u0430\u043b\u044c\u043d\u044b\u0439 \u043a\u043e\u043d\u043a\u0443\u0440\u0441</b>\n\n"
        "\U0001f6a7 \u0420\u0430\u0437\u0434\u0435\u043b \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f \u0432 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0435.\n"
        "\u0417\u0434\u0435\u0441\u044c \u0431\u0443\u0434\u0435\u0442 \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0440\u0435\u0444\u0435\u0440\u0430\u043b\u044c\u043d\u044b\u043c\u0438 \u043a\u043e\u043d\u043a\u0443\u0440\u0441\u0430\u043c\u0438.",
        reply_markup=admin_kb.stub_keyboard(),
    )


@router.callback_query(F.data == "admin_create_check")
async def admin_create_check_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "\u26a1 <b>\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0447\u0435\u043a</b>\n\n"
        "\U0001f6a7 \u0420\u0430\u0437\u0434\u0435\u043b \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f \u0432 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0435.\n"
        "\u0417\u0434\u0435\u0441\u044c \u0431\u0443\u0434\u0435\u0442 \u0441\u043e\u0437\u0434\u0430\u043d\u0438\u0435 \u0447\u0435\u043a\u043e\u0432 \u0434\u043b\u044f \u043f\u043e\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f \u0431\u0430\u043b\u0430\u043d\u0441\u0430.",
        reply_markup=admin_kb.stub_keyboard(),
    )


@router.callback_query(F.data == "admin_required_sub")
async def admin_required_sub_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "\U0001f4cc <b>\u041e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u0430\u044f \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0430</b>\n\n"
        "\U0001f6a7 \u0420\u0430\u0437\u0434\u0435\u043b \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f \u0432 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0435.\n"
        "\u0417\u0434\u0435\u0441\u044c \u043c\u043e\u0436\u043d\u043e \u043d\u0430\u0441\u0442\u0440\u043e\u0438\u0442\u044c \u043e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u0443\u044e \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443 \u043d\u0430 \u043a\u0430\u043d\u0430\u043b.",
        reply_markup=admin_kb.stub_keyboard(),
    )


@router.callback_query(F.data == "admin_premiums")
async def admin_premiums_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "\u2b50 <b>\u041f\u0440\u0435\u043c\u0438\u0443\u043c\u044b</b>\n\n"
        "\U0001f6a7 \u0420\u0430\u0437\u0434\u0435\u043b \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f \u0432 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0435.\n"
        "\u0417\u0434\u0435\u0441\u044c \u0431\u0443\u0434\u0435\u0442 \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043f\u0440\u0435\u043c\u0438\u0443\u043c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0430\u043c\u0438.",
        reply_markup=admin_kb.stub_keyboard(),
    )


@router.callback_query(F.data == "admin_gifts")
async def admin_gifts_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "\U0001f381 <b>\u041f\u043e\u0434\u0430\u0440\u043a\u0438</b>\n\n"
        "\U0001f6a7 \u0420\u0430\u0437\u0434\u0435\u043b \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f \u0432 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0435.\n"
        "\u0417\u0434\u0435\u0441\u044c \u0431\u0443\u0434\u0435\u0442 \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043f\u043e\u0434\u0430\u0440\u043a\u0430\u043c\u0438.",
        reply_markup=admin_kb.stub_keyboard(),
    )


@router.callback_query(F.data == "admin_autopay")
async def admin_autopay_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "\U0001f4b8 <b>\u0410\u0432\u0442\u043e\u043e\u043f\u043b\u0430\u0442\u0430</b>\n\n"
        "\U0001f6a7 \u0420\u0430\u0437\u0434\u0435\u043b \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f \u0432 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0435.\n"
        "\u0417\u0434\u0435\u0441\u044c \u0431\u0443\u0434\u0435\u0442 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u043e\u0439 \u043e\u043f\u043b\u0430\u0442\u044b.",
        reply_markup=admin_kb.stub_keyboard(),
    )


@router.callback_query(F.data == "admin_payment_system")
async def admin_payment_system_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "\U0001f4b3 <b>\u041f\u043b\u0430\u0442\u0451\u0436\u043d\u0430\u044f \u0441\u0438\u0441\u0442\u0435\u043c\u0430</b>\n\n"
        "\U0001f6a7 \u0420\u0430\u0437\u0434\u0435\u043b \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f \u0432 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0435.\n"
        "\u0417\u0434\u0435\u0441\u044c \u0431\u0443\u0434\u0435\u0442 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 \u043f\u043b\u0430\u0442\u0451\u0436\u043d\u044b\u0445 \u0441\u0438\u0441\u0442\u0435\u043c.",
        reply_markup=admin_kb.stub_keyboard(),
    )


@router.callback_query(F.data == "admin_stars_topup")
async def admin_stars_topup_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "\u2b50 <b>\u041f\u043e\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u0435 Stars</b>\n\n"
        "\U0001f6a7 \u0420\u0430\u0437\u0434\u0435\u043b \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f \u0432 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0435.\n"
        "\u0417\u0434\u0435\u0441\u044c \u0431\u0443\u0434\u0435\u0442 \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043f\u043e\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u0435\u043c Telegram Stars.",
        reply_markup=admin_kb.stub_keyboard(),
    )


@router.callback_query(F.data == "admin_admins_settings")
async def admin_admins_settings_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "\U0001f510 <b>\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u0430\u0434\u043c\u0438\u043d\u043e\u0432</b>\n\n"
        "\U0001f6a7 \u0420\u0430\u0437\u0434\u0435\u043b \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f \u0432 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0435.\n"
        "\u0417\u0434\u0435\u0441\u044c \u0431\u0443\u0434\u0435\u0442 \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u0430\u043c\u0438.",
        reply_markup=admin_kb.stub_keyboard(),
    )


@router.message(Command("confirm"))
async def cmd_confirm(message: Message):
    if not message.from_user:
        return
    if not _is_admin(message.from_user.id):
        await _deny(message)
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "\u274c \u0423\u043a\u0430\u0436\u0438\u0442\u0435 ID \u0437\u0430\u043a\u0430\u0437\u0430:\n\n"
            "<code>/confirm topup_abc123</code>",
        )
        return
    order_id = args[1].strip()
    await message.answer(f"\u23f3 \u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430: <code>{order_id}</code>...")
    from services.payment_client import confirm_payment
    result = await confirm_payment(order_id)
    if result.get("ok"):
        await message.answer(
            f"\u2705 <b>\u041f\u043b\u0430\u0442\u0451\u0436 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0451\u043d!</b>\n\n"
            f"\U0001f4e6 \u0417\u0430\u043a\u0430\u0437: <code>{order_id}</code>\n"
            f"\U0001f4b0 \u0421\u0443\u043c\u043c\u0430: {result.get('amount', 0):,} \u0441\u0443\u043c\n"
            f"\U0001f4b3 \u041d\u043e\u0432\u044b\u0439 \u0431\u0430\u043b\u0430\u043d\u0441: {result.get('new_balance', 0):,} \u0441\u0443\u043c",
        )
    elif "PAYMENT_SERVER_URL not configured" in result.get("error", ""):
        await _confirm_locally(message, order_id)
    else:
        unknown_error = "\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430\u044f \u043e\u0448\u0438\u0431\u043a\u0430"
        await message.answer(
            f"\u274c \u041e\u0448\u0438\u0431\u043a\u0430: {result.get('error', unknown_error)}",
        )


async def _confirm_locally(message: Message, order_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        order = await conn.fetchrow(
            "SELECT * FROM orders WHERE external_id = $1",
            order_id
        )
        if not order:
            await message.answer(f"\u274c \u0417\u0430\u043a\u0430\u0437 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d: <code>{order_id}</code>")
            return
        if order["status"] != "pending":
            await message.answer(f"\u26a0\ufe0f \u0417\u0430\u043a\u0430\u0437 <code>{order_id}</code> \u0443\u0436\u0435 \u0432 \u0441\u0442\u0430\u0442\u0443\u0441\u0435 \u00ab{order['status']}\u00bb")
            return
        tid = order["telegram_id"]
        amount = order["amount"]
        new_balance = await add_balance(tid, amount)
        await conn.execute(
            "UPDATE orders SET status = 'completed' WHERE external_id = $1",
            order_id
        )
        await record_payment(
            order_id, tid, amount, "paid",
            f'{{"source": "admin_confirm_local", "admin_id": {message.from_user.id}}}'
        )
        bot = Bot(
            token=config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        try:
            user_text = (
                f"<tg-emoji emoji-id=\"{config.CUSTOM_EMOJI_CHECK}\">\u2705</tg-emoji> "
                f"<b>\u041f\u043b\u0430\u0442\u0451\u0436 \u0443\u0441\u043f\u0435\u0448\u043d\u043e \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0451\u043d</b>\n\n"
                f"<tg-emoji emoji-id=\"{config.CUSTOM_EMOJI_WALLET}\">\U0001f45b</tg-emoji> "
                f"\u041d\u0430 \u0432\u0430\u0448 \u0441\u0447\u0451\u0442 \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u043e <b>{amount:,}</b> \u0441\u0443\u043c.\n"
                f"<tg-emoji emoji-id=\"{config.CUSTOM_EMOJI_MONEY}\">\U0001f4b0</tg-emoji> "
                f"\u041d\u043e\u0432\u044b\u0439 \u0431\u0430\u043b\u0430\u043d\u0441: <b>{new_balance:,}</b> \u0441\u0443\u043c"
            )
            await bot.send_message(tid, user_text)
        except Exception as e:
            logger.warning(f"Could not notify user {tid}: {e}")
        finally:
            await bot.session.close()
        user = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", tid)
        username = user["username"] if user else str(tid)
        await message.answer(
            f"\u2705 <b>\u041f\u043b\u0430\u0442\u0451\u0436 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0451\u043d!</b>\n\n"
            f"\U0001f464 \u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c: @{username}\n"
            f"\U0001f4e6 \u0417\u0430\u043a\u0430\u0437: <code>{order_id}</code>\n"
            f"\U0001f4b0 \u0421\u0443\u043c\u043c\u0430: {amount:,} \u0441\u0443\u043c\n"
            f"\U0001f4b3 \u041d\u043e\u0432\u044b\u0439 \u0431\u0430\u043b\u0430\u043d\u0441: {new_balance:,} \u0441\u0443\u043c\n\n"
            f"\U0001f4e8 \u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044e \u043e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u043e \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u0435.",
        )
