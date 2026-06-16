from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import settings


def _btn(
    text: str,
    *,
    web_app_url: str | None = None,
    callback_data: str | None = None,
    url: str | None = None,
    style: str | None = None,
    icon_custom_emoji_id: str | None = None,
) -> InlineKeyboardButton:
    kwargs: dict = {"text": text}
    if web_app_url:
        kwargs["web_app"] = WebAppInfo(url=web_app_url)
    if callback_data:
        kwargs["callback_data"] = callback_data
    if url:
        kwargs["url"] = url
    if style:
        kwargs["style"] = style
    if icon_custom_emoji_id:
        kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id
    return InlineKeyboardButton(**kwargs)


def main_inline_keyboard() -> InlineKeyboardMarkup:
    base = settings.webapp_base_url
    admin_url = "https://t.me/StarPayUzAdmin"
    wallet_emoji = settings.custom_emoji_wallet
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn(
                    "Webapp",
                    web_app_url=f"{base}/stars.html",
                    style="success",
                ),
            ],
            [
                _btn(
                    "Balans To'ldirish",
                    callback_data="topup",
                    style="primary",
                    icon_custom_emoji_id=wallet_emoji,
                ),
                _btn(
                    "Support",
                    url=admin_url,
                    style="danger",
                    icon_custom_emoji_id=settings.custom_emoji_user,
                ),
            ],
        ]
    )


def topup_back_keyboard() -> InlineKeyboardMarkup:
    """Back button for topup screen"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="◀️ Orqaga",
        callback_data="topup_back"
    ))
    return builder.as_markup()


def topup_payment_keyboard(order_id: str) -> InlineKeyboardMarkup:
    """Payment check + cancel buttons"""
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


def stars_keyboard() -> InlineKeyboardMarkup:
    """Stars purchase packages"""
    builder = InlineKeyboardBuilder()
    for amount, price in [
        (50, 10000), (75, 15000), (100, 20000),
        (250, 50000), (500, 100000),
    ]:
        builder.row(InlineKeyboardButton(
            text=f"⭐ {amount} Stars — {price:,} so'm",
            callback_data=f"buy_stars_{amount}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="refresh_menu"))
    return builder.as_markup()


def premium_keyboard() -> InlineKeyboardMarkup:
    """Premium subscription packages"""
    builder = InlineKeyboardBuilder()
    for duration, price, name in [
        (3, 160000, "3 oy"), (6, 225000, "6 oy"), (12, 380000, "12 oy"),
    ]:
        builder.row(InlineKeyboardButton(
            text=f"💎 Premium {name} — {price:,} so'm",
            callback_data=f"buy_premium_{duration}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="refresh_menu"))
    return builder.as_markup()


def bosh_menu_keyboard() -> InlineKeyboardMarkup:
    """Blue Bosh Menu button"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🏠 Bosh Menu",
        callback_data="refresh_menu",
        style="primary",
    ))
    return builder.as_markup()


def bottom_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💰 Narxlar"),
                KeyboardButton(text="📚 Qo'llanma"),
            ],
            [KeyboardButton(text="🔄 Tilni almashtirish")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
