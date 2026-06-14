"""
Скрипт для скачивания картинок NFT подарков из Telegram.
Сохраняет превью (thumbnail) каждого подарка как .webp файл.

Запуск: python download_gift_images.py
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION = os.getenv("TELETHON_SESSION_STRING", "") or os.getenv("SESSION_NAME", "starpayuz_session")

OUTPUT_DIR = "webapp/images/gifts"
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def download_gift_images():
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.tl.functions.payments import GetStarGiftsRequest

    # Используем StringSession если есть, иначе файловую сессию
    if SESSION and len(SESSION) > 50:
        session = StringSession(SESSION)
    else:
        session = SESSION

    client = TelegramClient(session, API_ID, API_HASH)
    await client.start()

    print("✅ Подключён к Telegram")

    result = await client(GetStarGiftsRequest(hash=0))

    print(f"📦 Найдено {len(result.gifts)} подарков\n")

    for gift in result.gifts:
        gift_id = str(gift.id)
        stars = getattr(gift, 'stars', 0)
        limited = getattr(gift, 'limited', False)
        avail = getattr(gift, 'availability_remains', None)
        total = getattr(gift, 'availability_total', None)

        label = f"[LIMITED {avail}/{total}]" if limited else ""
        print(f"🎁 ID: {gift_id}  Stars: {stars}  {label}")

        # Скачиваем thumbnail стикера
        if hasattr(gift, 'sticker') and gift.sticker:
            sticker = gift.sticker

            # Получаем thumbnail (маленькая картинка .webp)
            thumb_path = f"{OUTPUT_DIR}/gift_{gift_id}.webp"

            if os.path.exists(thumb_path):
                print(f"   ⏭  Уже скачан: {thumb_path}")
                continue

            try:
                # Скачиваем как bytes
                data = await client.download_media(sticker, bytes)
                if data:
                    with open(thumb_path, 'wb') as f:
                        f.write(data)
                    size_kb = len(data) / 1024
                    print(f"   ✅ Сохранён: {thumb_path} ({size_kb:.1f} KB)")
                else:
                    print(f"   ⚠️  Нет данных для {gift_id}")
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")

    await client.disconnect()
    print("\n🎉 Готово! Картинки сохранены в:", OUTPUT_DIR)
    print("\n📋 Список файлов:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        path = f"{OUTPUT_DIR}/{f}"
        size = os.path.getsize(path) / 1024
        print(f"   {f}  ({size:.1f} KB)")


if __name__ == "__main__":
    asyncio.run(download_gift_images())
