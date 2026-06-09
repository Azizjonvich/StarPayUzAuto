import os
from dotenv import load_dotenv

load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")

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
        "info": "Premium sovg'alar"
    }
}
