from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

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
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn(
                    "Webapp",
                    web_app_url=f"{base}/stars.html",
                    style="primary",
                ),
            ],
            [
                _btn("@StarPayUzAdmin", url=admin_url, style="danger"),
                _btn("@StarPayUzAdmin", url=admin_url, style="success"),
            ],
        ]
    )


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
