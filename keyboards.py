from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    WebAppInfo
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
import config


def get_webapp_main_keyboard() -> InlineKeyboardMarkup:
    """Main inline menu: Webapp + admin contact buttons"""
    builder = InlineKeyboardBuilder()
    admin_url = "https://t.me/StarPayUzAdmin"

    builder.row(
        InlineKeyboardButton(
            text="Webapp",
            web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/stars.html"),
            style="primary",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Balans To'ldirish",
            callback_data="topup_menu"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="@StarPayUzAdmin",
            url=admin_url,
            style="danger",
        ),
        InlineKeyboardButton(
            text="@StarPayUzAdmin",
            url=admin_url,
            style="success",
        ),
    )

    return builder.as_markup()


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Simple reply keyboard"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="🏠 Bosh menyu")
    )
    
    return builder.as_markup(resize_keyboard=True)


def get_stars_keyboard() -> InlineKeyboardMarkup:
    """Stars purchase keyboard"""
    builder = InlineKeyboardBuilder()
    
    for package in config.PRODUCTS["stars"]["packages"]:
        amount = package["amount"]
        price = package["price"]
        builder.row(
            InlineKeyboardButton(
                text=f"⭐ {amount} Stars - {price:,} so'm",
                callback_data=f"buy_stars_{amount}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")
    )
    
    return builder.as_markup()


def get_premium_keyboard() -> InlineKeyboardMarkup:
    """Premium purchase keyboard with premium emoji"""
    builder = InlineKeyboardBuilder()
    
    for package in config.PRODUCTS["premium"]["packages"]:
        duration = package["duration"]
        price = package["price"]
        name = package["name"]
        builder.row(
            InlineKeyboardButton(
                text=f"💎 Premium {name} - {price:,} so'm",
                callback_data=f"buy_premium_{duration}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")
    )
    
    return builder.as_markup()


def get_payment_keyboard(payment_url: str, order_id: str) -> InlineKeyboardMarkup:
    """Payment keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💳 To'lash", url=payment_url)
    )
    builder.row(
        InlineKeyboardButton(text="✅ To'lovni tekshirish", callback_data=f"check_payment_{order_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_order_{order_id}")
    )
    
    return builder.as_markup()


def get_webapp_keyboard() -> ReplyKeyboardMarkup:
    """Web App keyboard"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(
            text="🛒 Magazin ochish",
            web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/index.html")
        )
    )
    builder.row(
        KeyboardButton(text="◀️ Orqaga")
    )
    
    return builder.as_markup(resize_keyboard=True)


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Admin panel main menu"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"))
    builder.row(InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users"))
    builder.row(InlineKeyboardButton(text="💰 Balans boshqaruvi", callback_data="admin_balance"))
    builder.row(InlineKeyboardButton(text="💳 To'lovni tasdiqlash", callback_data="admin_confirm_payments"))
    builder.row(InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin_broadcast"))
    builder.row(InlineKeyboardButton(text="📦 Buyurtmalar", callback_data="admin_orders"))
    builder.row(InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin_settings"))
    return builder.as_markup()


def get_admin_payments_keyboard(orders: list, page: int = 1, total: int = 0) -> InlineKeyboardMarkup:
    """Pending payments list with confirm buttons"""
    builder = InlineKeyboardBuilder()
    for o in orders:
        label = f"💰 #{o['id']} — {o.get('telegram_id', '?')} — {o.get('amount', 0):,} so'm"
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"admin_pay_detail_{o['id']}"
        ))
    # Pagination
    has_next = (page * 5) < total
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_pay_page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page}", callback_data="admin_pay_skip"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_pay_page_{page+1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_main_menu"))
    return builder.as_markup()


def get_admin_pay_confirm_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Confirm or reject a payment"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ To'lov keldi — Balansni to'ldirish",
            callback_data=f"admin_pay_confirm_{order_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Bekor qilish",
            callback_data=f"admin_pay_reject_{order_id}"
        )
    )
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_confirm_payments"))
    return builder.as_markup()


def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    """Back to admin main menu"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_main_menu"))
    return builder.as_markup()


def get_admin_users_keyboard() -> InlineKeyboardMarkup:
    """Users management menu"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Ro'yxat", callback_data="admin_users_list_1"))
    builder.row(InlineKeyboardButton(text="🔍 Qidirish", callback_data="admin_users_search"))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_main_menu"))
    return builder.as_markup()


def get_admin_users_list_keyboard(page: int, has_next: bool) -> InlineKeyboardMarkup:
    """Users list pagination"""
    builder = InlineKeyboardBuilder()
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_users_list_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page}", callback_data="admin_users_list_skip"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_users_list_{page+1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_users"))
    return builder.as_markup()


def get_admin_user_actions_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """Single user actions"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔒 Bloklash", callback_data=f"admin_user_block_{telegram_id}"),
        InlineKeyboardButton(text="🔓 Blokdan chiqarish", callback_data=f"admin_user_unblock_{telegram_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin_user_delete_{telegram_id}"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_users"))
    return builder.as_markup()


def get_admin_orders_keyboard(orders: list, page: int = 1, total: int = 0) -> InlineKeyboardMarkup:
    """Orders list with clickable order buttons + pagination"""
    builder = InlineKeyboardBuilder()
    for o in orders:
        status_emoji = {"pending": "⏳", "processing": "🔄", "completed": "✅",
                        "failed": "❌", "cancelled": "🚫"}.get(o["status"], "❓")
        label = f"{status_emoji} #{o['id']} — {o.get('product_type', '?')}"
        builder.row(InlineKeyboardButton(
            text=label, callback_data=f"admin_order_detail_{o['id']}"
        ))
    # Pagination
    has_next = (page * 5) < total
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_orders_page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page}", callback_data="admin_orders_skip"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_orders_page_{page+1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_main_menu"))
    return builder.as_markup()


def get_admin_order_detail_keyboard(order_id: int, current_status: str) -> InlineKeyboardMarkup:
    """Order detail actions"""
    builder = InlineKeyboardBuilder()
    statuses = ["pending", "processing", "completed", "failed", "cancelled"]
    for s in statuses:
        if s != current_status:
            builder.row(InlineKeyboardButton(
                text=f"➡️ {s.title()}", callback_data=f"admin_order_status_{order_id}_{s}"
            ))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_orders"))
    return builder.as_markup()


def get_admin_balance_actions_keyboard() -> InlineKeyboardMarkup:
    """Balance actions: add or deduct"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Qo'shish", callback_data="admin_balance_act_add"),
        InlineKeyboardButton(text="➖ Ayirish", callback_data="admin_balance_act_deduct"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_main_menu"))
    return builder.as_markup()


def get_admin_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Broadcast confirm: Yes/No"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yuborish", callback_data="admin_broadcast_confirm"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_broadcast_cancel"),
    )
    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Legacy admin panel keyboard"""
    return get_admin_main_keyboard()


def get_confirm_keyboard(action: str, data: str) -> InlineKeyboardMarkup:
    """Confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Ha", callback_data=f"confirm_{action}_{data}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data=f"cancel_{action}")
    )
    
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Simple back button"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")
    )
    return builder.as_markup()


def get_card_payment_keyboard(order_id: str) -> InlineKeyboardMarkup:
    """Card payment: check + cancel buttons"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ To'lovni tekshirish",
            callback_data=f"check_payment_{order_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Bekor qilish",
            callback_data=f"cancel_order_{order_id}"
        )
    )
    return builder.as_markup()
