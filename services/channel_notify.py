import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config

logger = logging.getLogger(__name__)

CHANNEL_ID = config.CHANNEL_ORDERS


def _emoji(emoji_id: str | None, fallback: str) -> str:
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback


def _get_gift_emoji(gift_id: str) -> str:
    mapping = {
        "heart": _emoji(config.EMOJI_HEART, "💝"),
        "bear": _emoji(config.EMOJI_BEAR, "🧸"),
        "box": _emoji(config.EMOJI_BOX, "🎁"),
        "rose": _emoji(config.EMOJI_ROSE, "🌹"),
        "cake": _emoji(config.EMOJI_CAKE, "🎂"),
        "rocket": _emoji(config.EMOJI_ROCKET_GIFT, "🚀"),
        "champagne": _emoji(config.EMOJI_ROCKET_GIFT, "🍾"),
        "bouquet": _emoji(config.EMOJI_BOUQUET, "💐"),
        "diamond": _emoji(config.EMOJI_DIAMOND, "💎"),
        "trophy": _emoji(config.EMOJI_TROPHY, "🏆"),
        "ring": _emoji(config.EMOJI_RING, "💍"),
    }
    return mapping.get(gift_id, "🎁")


async def notify_stars(username: str, quantity: int, price: int) -> None:
    star_e = _emoji(config.EMOJI_STAR, "⭐️")
    target_e = _emoji(config.EMOJI_TARGET, "🎯")
    amount_e = _emoji(config.EMOJI_STARS_AMOUNT, "💫")
    money_e = _emoji(config.EMOJI_MONEY_CH, "💰")
    rocket_e = _emoji(config.EMOJI_ROCKET, "🚀")

    text = (
        f"{star_e} <b>Stars muvaffaqiyatli yuborildi!</b>\n\n"
        f"{target_e} Qabul qiluvchi: @{username}\n"
        f"{amount_e} Miqdor: {quantity:,} Stars\n"
        f"{money_e} Summa: {price:,} so'm\n\n"
        f"{rocket_e} Stars hisobiga muvaffaqiyatli tushirildi!"
    )
    await _send(text)


async def notify_premium(username: str, months: int, price: int) -> None:
    star_e = _emoji(config.EMOJI_STAR, "⭐️")
    target_e = _emoji(config.EMOJI_TARGET, "🎯")
    calendar_e = _emoji(config.EMOJI_CALENDAR, "📅")
    money_e = _emoji(config.EMOJI_MONEY_CH, "💰")
    rocket_e = _emoji(config.EMOJI_ROCKET, "🚀")

    text = (
        f"{star_e} <b>Premium muvaffaqiyatli yuborildi!</b>\n\n"
        f"{target_e} Qabul qiluvchi: @{username}\n"
        f"{calendar_e} Muddat: {months} oy\n"
        f"{money_e} Summa: {price:,} so'm\n\n"
        f"{rocket_e} Premium muvaffaqiyatli faollashtirildi!"
    )
    await _send(text)


async def notify_gift(username: str, gift_id: str, gift_name: str, price: int) -> None:
    gift_header_e = _emoji(config.EMOJI_GIFT, "🎁")
    target_e = _emoji(config.EMOJI_TARGET, "🎯")
    amount_e = _emoji(config.EMOJI_STARS_AMOUNT, "💫")
    gift_emoji = _get_gift_emoji(gift_id)
    money_e = _emoji(config.EMOJI_MONEY_CH, "💰")
    rocket_e = _emoji(config.EMOJI_ROCKET_GIFT, "🚀")

    text = (
        f"{gift_header_e} <b>Telegram Gift muvaffaqiyatli yuborildi!</b>\n\n"
        f"{target_e} Qabul qiluvchi: @{username}\n"
        f"{amount_e} Gift: {gift_emoji}\n"
        f"{money_e} Summa: {price:,} so'm\n\n"
        f"{rocket_e} Gift muvaffaqiyatli yetkazildi!"
    )
    await _send(text)


async def _send(text: str) -> None:
    if not config.BOT_TOKEN:
        logger.warning("BOT_TOKEN not set, skipping channel notification")
        return
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        await bot.send_message(CHANNEL_ID, text)
        logger.info("Notification sent to %s", CHANNEL_ID)
    except Exception as e:
        logger.warning("Failed to send channel notification to %s: %s", CHANNEL_ID, e)
    finally:
        await bot.session.close()
