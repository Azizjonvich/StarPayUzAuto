import os
from dotenv import load_dotenv

load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Telethon (User Client for sending gifts)
# Optional - if not set, gift sending will be disabled
try:
    API_ID = int(os.getenv("API_ID", "0") or "0")
except (ValueError, TypeError):
    API_ID = 0

API_HASH = os.getenv("API_HASH", "")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")  # Your phone number for user account
SESSION_NAME = os.getenv("SESSION_NAME", "starpay_session")
TELETHON_SESSION_STRING = os.getenv("TELETHON_SESSION_STRING", "")  # String session for Railway

# Fragment API settings
FRAGMENT_API_KEY = os.getenv("FRAGMENT_API_KEY")
FRAGMENT_API_URL = os.getenv("FRAGMENT_API_URL", "https://fragment-api.uz/api")

# Shop settings
SHOP_ID = os.getenv("SHOP_ID")
SHOP_KEY = os.getenv("SHOP_KEY")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database.db")

# Web App
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://starpayuz-webapp.vercel.app")

# Admin IDs
ADMINS = [8784918764]

# Allowed usernames (for access control) - comma separated
ALLOWED_USERNAMES = os.getenv("ALLOWED_USERNAMES", "StarPayUzAdmin").split(",")
# Пример: ALLOWED_USERNAMES=StarPayUzAdmin,user2,user3

# Stars limits (Fragment API minimum is 50)
STARS_MIN_AMOUNT = 50
STARS_MAX_AMOUNT = 1_000_000

# Products configuration
PRODUCTS = {
    "stars": {
        "name": "⭐ Stars olish",
        "emoji": "⭐",
        "color": "#FFD700",
        "min_amount": STARS_MIN_AMOUNT,
        "max_amount": STARS_MAX_AMOUNT,
        "packages": [
            {"amount": 50, "price": 10000},
            {"amount": 75, "price": 15000},
            {"amount": 100, "price": 20000},
            {"amount": 250, "price": 50000},
            {"amount": 500, "price": 100000},
        ]
    },
    "premium": {
        "name": "💎 Premium olish",
        "emoji": "💎",
        "color": "#00BFFF",
        "is_premium": True,
        "packages": [
            {"duration": 3, "price": 160000, "name": "3 oy"},
            {"duration": 6, "price": 225000, "name": "6 oy"},
            {"duration": 12, "price": 380000, "name": "12 oy"},
        ]
    },
    "phone": {
        "name": "📱 Nomer olish",
        "emoji": "📱",
        "color": "#808080",
        "info": "Virtual raqamlar"
    },
    "gift": {
        "name": "🎁 Gift olish",
        "emoji": "🎁",
        "color": "#FF69B4",
        "info": "Premium sovg'alar",
        "packages": [
            # Обычные подарки (Regular Gifts)
            {"id": "heart", "name": "Yurak", "price": 3000, "emoji": "💝", "stars": 1, "tier": "regular"},
            {"id": "bear", "name": "Ayiq", "price": 3000, "emoji": "🧸", "stars": 1, "tier": "regular"},
            {"id": "box", "name": "Quti", "price": 5000, "emoji": "🎁", "stars": 1, "tier": "regular"},
            {"id": "rose", "name": "Atirgul", "price": 5000, "emoji": "🌹", "stars": 1, "tier": "regular"},
            {"id": "cake", "name": "Tort", "price": 10000, "emoji": "🎂", "stars": 2, "tier": "regular"},
            {"id": "rocket", "name": "Raketa", "price": 10000, "emoji": "🚀", "stars": 2, "tier": "regular"},
            {"id": "champagne", "name": "Shampan", "price": 10000, "emoji": "🍾", "stars": 2, "tier": "regular"},
            {"id": "bouquet", "name": "Guldasta", "price": 10000, "emoji": "💐", "stars": 2, "tier": "regular"},
            {"id": "diamond", "name": "Olmos", "price": 20000, "emoji": "💎", "stars": 5, "tier": "regular"},
            {"id": "trophy", "name": "Kubok", "price": 20000, "emoji": "🏆", "stars": 5, "tier": "regular"},
            {"id": "ring", "name": "Uzuk", "price": 20000, "emoji": "💍", "stars": 5, "tier": "regular"},
            
            # Удалённые/Премиум подарки (Deluxe/Limited Gifts)
            {"id": "deluxe_rose", "name": "Deluxe Atirgul", "price": 50000, "emoji": "🌹✨", "stars": 25, "tier": "deluxe", "limited": True},
            {"id": "deluxe_heart", "name": "Deluxe Yurak", "price": 50000, "emoji": "💝✨", "stars": 25, "tier": "deluxe", "limited": True},
            {"id": "deluxe_cake", "name": "Deluxe Tort", "price": 75000, "emoji": "🎂✨", "stars": 50, "tier": "deluxe", "limited": True},
            {"id": "deluxe_diamond", "name": "Deluxe Olmos", "price": 100000, "emoji": "💎✨", "stars": 100, "tier": "deluxe", "limited": True},
            {"id": "golden_trophy", "name": "Oltin Kubok", "price": 150000, "emoji": "🏆✨", "stars": 250, "tier": "premium", "limited": True},
            {"id": "star_crown", "name": "Yulduz Toj", "price": 200000, "emoji": "👑✨", "stars": 500, "tier": "premium", "limited": True},
            {"id": "blue_gem", "name": "Ko'k Javohir", "price": 250000, "emoji": "💠", "stars": 1000, "tier": "premium", "limited": True},
            {"id": "fire_phoenix", "name": "Olovli Qanot", "price": 500000, "emoji": "🔥🦅", "stars": 2500, "tier": "exclusive", "limited": True},
        ]
    }
}
