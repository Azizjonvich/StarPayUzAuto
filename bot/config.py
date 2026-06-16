import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _list_ints(value: str) -> list[int]:
    if not value.strip():
        return []
    return [int(x.strip()) for x in value.split(",") if x.strip().isdigit()]


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    fragment_api_key: str
    fragment_api_base: str
    shop_id: str
    shop_key: str
    webapp_base_url: str
    api_public_url: str
    support_url: str
    admin_ids: list[int]
    api_host: str
    api_port: int
    custom_emoji_star: str | None
    custom_emoji_premium: str | None
    custom_emoji_gift: str | None
    custom_emoji_phone: str | None
    custom_emoji_check: str | None
    custom_emoji_money: str | None
    custom_emoji_wallet: str | None
    custom_emoji_cross: str | None
    custom_emoji_down: str | None
    custom_emoji_up: str | None
    custom_emoji_id_icon: str | None
    custom_emoji_card: str | None
    custom_emoji_user: str | None
    custom_emoji_clock: str | None
    custom_emoji_warn: str | None
    admin_panel_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        base = (
            os.getenv("WEBAPP_BASE_URL")
            or os.getenv("WEBAPP_URL")
            or "http://localhost:8080"
        ).rstrip("/")
        # Clean API key - remove all whitespace including newlines
        raw_api_key = os.getenv("FRAGMENT_API_KEY") or os.getenv("FRAGMENT_API_KEY", "")
        clean_api_key = "".join(raw_api_key.split()) if raw_api_key else ""
        
        return cls(
            bot_token=os.getenv("BOT_TOKEN", ""),
            fragment_api_key=clean_api_key,
            fragment_api_base=os.getenv("FRAGMENT_API_BASE")
                or os.getenv("FRAGMENT_API_URL", "https://fragment-api.uz/api/v1").rstrip("/"),
            shop_id=os.getenv("SHOP_ID", "").strip(),
            shop_key=os.getenv("SHOP_KEY", "").strip(),
            webapp_base_url=base,
            api_public_url=(
                os.getenv("API_PUBLIC_URL")
                or os.getenv("API_BASE_URL")
                or base
            ).rstrip("/"),
            support_url=os.getenv("SUPPORT_URL", "https://t.me/"),
            admin_ids=_list_ints(os.getenv("ADMIN_IDS", "")),
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("PORT") or os.getenv("API_PORT", "8080")),
            custom_emoji_star=os.getenv("CUSTOM_EMOJI_STAR") or None,
            custom_emoji_premium=os.getenv("CUSTOM_EMOJI_PREMIUM") or "6053186856688814091",
            custom_emoji_gift=os.getenv("CUSTOM_EMOJI_GIFT") or None,
            custom_emoji_phone=os.getenv("CUSTOM_EMOJI_PHONE") or None,
            custom_emoji_check=os.getenv("CUSTOM_EMOJI_CHECK") or "5980930633298350051",
            custom_emoji_money=os.getenv("CUSTOM_EMOJI_MONEY") or "5811989245761426317",
            custom_emoji_wallet=os.getenv("CUSTOM_EMOJI_WALLET") or "5987880246865565644",
            custom_emoji_cross=os.getenv("CUSTOM_EMOJI_CROSS") or "5273914604752216432",
            custom_emoji_down=os.getenv("CUSTOM_EMOJI_DOWN") or "5229212516415978792",
            custom_emoji_up=os.getenv("CUSTOM_EMOJI_UP") or "5229113938326599381",
            custom_emoji_id_icon=os.getenv("CUSTOM_EMOJI_ID") or "5818885490065017876",
            custom_emoji_card=os.getenv("CUSTOM_EMOJI_CARD") or "5927169041595634481",
            custom_emoji_user=os.getenv("CUSTOM_EMOJI_USER") or "5260399854500191689",
            custom_emoji_clock=os.getenv("CUSTOM_EMOJI_CLOCK") or "5316591603123502631",
            custom_emoji_warn=os.getenv("CUSTOM_EMOJI_WARN") or "5881702736843511327",
            admin_panel_url=os.getenv("ADMIN_PANEL_URL", "http://localhost:8000"),
        )


STARS_MIN_AMOUNT = 50
STARS_MAX_AMOUNT = 1_000_000

settings = Settings.from_env()
