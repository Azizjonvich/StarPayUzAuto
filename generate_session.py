"""
Скрипт для генерации Telethon string session
Запустите локально один раз для авторизации
"""

import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv
import os

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")


async def main():
    print("=== Telethon String Session Generator ===\n")
    
    if not API_ID or not API_HASH:
        print("❌ Ошибка: API_ID и API_HASH не настроены в .env")
        return
    
    print(f"API_ID: {API_ID}")
    print(f"API_HASH: {API_HASH[:10]}...")
    print(f"Phone: {PHONE_NUMBER}\n")
    
    # Используем StringSession вместо файла
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    
    await client.start(phone=PHONE_NUMBER)
    
    print("\n✅ Успешная авторизация!")
    print("\n" + "="*60)
    print("📝 Ваша STRING SESSION (скопируйте в Railway):")
    print("="*60)
    print(client.session.save())
    print("="*60)
    print("\nДобавьте в Railway Environment Variables:")
    print("TELETHON_SESSION_STRING=<скопированная_строка_выше>")
    print("\n⚠️  НЕ ПУБЛИКУЙТЕ ЭТУ СТРОКУ В GIT!")
    
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
