from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
    )
    builder.row(
        InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings"),
    )
    builder.row(
        InlineKeyboardButton(text="🔴 Управление пользователями", callback_data="admin_users")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Реферальный конкурс", callback_data="admin_ref_contest"),
        InlineKeyboardButton(text="⚡ Создать чек", callback_data="admin_create_check"),
    )
    builder.row(
        InlineKeyboardButton(text="📌 Обязательная подписка", callback_data="admin_required_sub"),
        InlineKeyboardButton(text="⭐ Премиумы", callback_data="admin_premiums"),
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Подарки", callback_data="admin_gifts"),
        InlineKeyboardButton(text="💸 Автооплата", callback_data="admin_autopay"),
    )
    builder.row(
        InlineKeyboardButton(text="💳 Платёжная система", callback_data="admin_payment_system"),
        InlineKeyboardButton(text="⭐ Пополнение Stars", callback_data="admin_stars_topup"),
    )
    builder.row(
        InlineKeyboardButton(text="🔐 Настройки админов", callback_data="admin_admins_settings")
    )

    return builder.as_markup()


def back_button(callback_data: str = "admin_main_menu") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data)
    )
    return builder.as_markup()


def stats_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main_menu"),
    )
    return builder.as_markup()


def users_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_users_list_1"),
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Поиск", callback_data="admin_users_search"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main_menu"),
    )
    return builder.as_markup()


def users_list_keyboard(page: int, has_next: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_users_list_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page}", callback_data="admin_users_list_skip"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_users_list_{page+1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users"))
    return builder.as_markup()


def user_actions_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔒 Блокировать", callback_data=f"admin_user_block_{telegram_id}"),
        InlineKeyboardButton(text="🔓 Разблокировать", callback_data=f"admin_user_unblock_{telegram_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_user_delete_{telegram_id}"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users"))
    return builder.as_markup()


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Отправить", callback_data="admin_broadcast_confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast_cancel"),
    )
    return builder.as_markup()


def stub_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main_menu"),
    )
    return builder.as_markup()
