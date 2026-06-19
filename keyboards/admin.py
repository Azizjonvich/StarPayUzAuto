from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")
    )
    builder.row(
        InlineKeyboardButton(text="📨 Xabar yuborish", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin_settings"),
    )
    builder.row(
        InlineKeyboardButton(text="🔴 Foydalanuvchilar", callback_data="admin_users")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Referal konkurs", callback_data="admin_ref_contest"),
        InlineKeyboardButton(text="⚡ Chek yaratish", callback_data="admin_create_check"),
    )
    builder.row(
        InlineKeyboardButton(text="📌 Majburiy obuna", callback_data="admin_required_sub"),
        InlineKeyboardButton(text="⭐ Premiumlar", callback_data="admin_premiums"),
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Sovg'alar", callback_data="admin_gifts"),
        InlineKeyboardButton(text="💸 Avtoto'lov", callback_data="admin_autopay"),
    )
    builder.row(
        InlineKeyboardButton(text="💳 To'lov tizimi", callback_data="admin_payment_system"),
        InlineKeyboardButton(text="⭐ Stars to'ldirish", callback_data="admin_stars_topup"),
    )
    builder.row(
        InlineKeyboardButton(text="🔐 Admin sozlamalari", callback_data="admin_admins_settings")
    )

    return builder.as_markup()


def back_button(callback_data: str = "admin_main_menu") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data=callback_data)
    )
    return builder.as_markup()


def stats_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_stats"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_main_menu"),
    )
    return builder.as_markup()


def users_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Foydalanuvchilar ro'yxati", callback_data="admin_users_list_1"),
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Qidirish", callback_data="admin_users_search"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_main_menu"),
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
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_users"))
    return builder.as_markup()


def user_actions_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔒 Bloklash", callback_data=f"admin_user_block_{telegram_id}"),
        InlineKeyboardButton(text="🔓 Blokdan chiqarish", callback_data=f"admin_user_unblock_{telegram_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin_user_delete_{telegram_id}"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_users"))
    return builder.as_markup()


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yuborish", callback_data="admin_broadcast_confirm"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_broadcast_cancel"),
    )
    return builder.as_markup()


def check_confirm_keyboard(sp_id: int, amount: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admin_check_confirm_{sp_id}_{amount}"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_create_check"),
    )
    return builder.as_markup()


def ref_contest_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏆 Top reyting", callback_data="admin_ref_rating"),
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Konkurs sozlamalari", callback_data="admin_ref_settings"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_main_menu"),
    )
    return builder.as_markup()


def required_sub_keyboard(channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.row(InlineKeyboardButton(
            text=f"❌ {ch}", callback_data=f"admin_sub_del_{ch}"
        ))
    builder.row(
        InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="admin_sub_add"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_main_menu"),
    )
    return builder.as_markup()


def premiums_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Premium foydalanuvchilar", callback_data="admin_premiums_list"),
    )
    builder.row(
        InlineKeyboardButton(text="➕ Premium berish", callback_data="admin_premiums_grant"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_main_menu"),
    )
    return builder.as_markup()


def gifts_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_gifts"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_main_menu"),
    )
    return builder.as_markup()


def autopay_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    status = "✅ Yoqilgan" if enabled else "❌ O'chirilgan"
    builder.row(
        InlineKeyboardButton(text=status, callback_data="admin_autopay_toggle"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_main_menu"),
    )
    return builder.as_markup()


def payment_system_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Tekshirish", callback_data="admin_payment_system"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_main_menu"),
    )
    return builder.as_markup()


def stars_topup_confirm_keyboard(sp_id: int, amount: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admin_stars_confirm_{sp_id}_{amount}"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_stars_topup"),
    )
    return builder.as_markup()


def admins_keyboard(admin_ids: list[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for aid in admin_ids:
        builder.row(InlineKeyboardButton(
            text=f"❌ Admin {aid}", callback_data=f"admin_admin_del_{aid}"
        ))
    builder.row(
        InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="admin_admin_add"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_main_menu"),
    )
    return builder.as_markup()
