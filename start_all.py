#!/usr/bin/env python
"""Start both Telegram bot and aiohttp API server in one process."""
import asyncio
import logging
import sys

from aiohttp import web

from bot.config import settings
from api.server import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run_bot():
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    import config
    import database
    from handlers import start, shop, balance, profile, webapp, admin

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage_cls = __import__("aiogram.fsm.storage.memory", fromlist=["MemoryStorage"]).MemoryStorage
    dp = Dispatcher(storage=storage_cls())
    dp.include_router(start.router)
    dp.include_router(webapp.router)
    dp.include_router(shop.router)
    dp.include_router(balance.router)
    dp.include_router(profile.router)
    dp.include_router(admin.router)

    await database.init_db()
    logger.info("Bot starting...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def run_api():
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.api_host, settings.api_port)
    await site.start()
    logger.info("API server started on %s:%s", settings.api_host, settings.api_port)
    # Keep running
    while True:
        await asyncio.sleep(3600)


async def main():
    await asyncio.gather(
        run_bot(),
        run_api(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped")
