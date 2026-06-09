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


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Admin panel keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin_broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users")
    )
    
    return builder.as_markup()


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
