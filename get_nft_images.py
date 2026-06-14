"""
Получение картинок NFT подарков Telegram через og:image мета-теги.
Запуск: python get_nft_images.py
"""

import asyncio
import os
import re
import aiohttp

# NFT подарки которые хотим добавить в магазин
# Формат: (slug, номер_или_None_для_превью_коллекции)
NFT_GIFTS = [
    "SnoopDogg",
    "TrumpEternal", 
    "DurovCap",
    "HmstrCombat",
    "Plush",
    "JellyBunny",
    "RocketBoy",
    "DiamondRing",
    "SpookyPotion",
    "CactusDance",
]

OUTPUT_DIR = "webapp/images/nft"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Telegram Bot)",
    "Accept": "text/html,application/xhtml+xml",
}


async def get_og_image(session: aiohttp.ClientSession, slug: str, number: int = 1) -> str | None:
    """Получить og:image URL со страницы t.me/nft/"""
    url = f"https://t.me/nft/{slug}-{number}"
    try:
        async with session.get(url, headers=HEADERS, allow_redirects=True) as r:
            if r.status != 200:
                return None
            html = await r.text()
            # Ищем og:image
            match = re.search(r'<meta property="og:image"\s+content="([^"]+)"', html)
            if match:
                return match.group(1)
            # Альтернативный формат
            match = re.search(r'<meta content="([^"]+)"\s+property="og:image"', html)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"  ❌ Error fetching {url}: {e}")
    return None


async def download_image(session: aiohttp.ClientSession, url: str, path: str) -> bool:
    """Скачать картинку по URL"""
    try:
        async with session.get(url, headers=HEADERS) as r:
            if r.status == 200:
                data = await r.read()
                with open(path, 'wb') as f:
                    f.write(data)
                return True
    except Exception as e:
        print(f"  ❌ Download error: {e}")
    return False


async def main():
    print("🎁 Скачиваем превью NFT подарков из Telegram\n")
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for slug in NFT_GIFTS:
            print(f"🔍 {slug}...")
            
            # Пробуем получить картинку (номер 1 для превью)
            img_url = await get_og_image(session, slug, 1)
            
            if img_url:
                # Определяем расширение
                ext = ".jpg"
                if ".webp" in img_url: ext = ".webp"
                elif ".png" in img_url: ext = ".png"
                elif ".gif" in img_url: ext = ".gif"
                
                filename = f"nft_{slug.lower()}{ext}"
                filepath = f"{OUTPUT_DIR}/{filename}"
                
                ok = await download_image(session, img_url, filepath)
                if ok:
                    size_kb = os.path.getsize(filepath) / 1024
                    print(f"  ✅ Сохранено: {filename} ({size_kb:.1f} KB)")
                    print(f"     URL: {img_url}")
                    results.append({"slug": slug, "file": filename, "url": img_url})
                else:
                    print(f"  ⚠️  Не удалось скачать: {img_url}")
                    results.append({"slug": slug, "file": None, "url": img_url})
            else:
                print(f"  ⚠️  og:image не найден для {slug}")
                results.append({"slug": slug, "file": None, "url": None})
            
            await asyncio.sleep(0.5)  # не спамим
    
    print(f"\n{'='*50}")
    print(f"✅ Готово! Скачано {sum(1 for r in results if r['file'])} из {len(results)}")
    print(f"📁 Папка: {OUTPUT_DIR}")
    print()
    print("📋 Для использования в gift.html:")
    print()
    for r in results:
        if r['file']:
            print(f'  <img src="./images/nft/{r["file"]}" alt="{r["slug"]}">')


if __name__ == "__main__":
    asyncio.run(main())
