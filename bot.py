import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

import config
from services import database
from handlers import start, shop, balance, profile, webapp, admin
from middlewares import AccessControlMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log startup env vars (no secrets)
logger.info("=== STARTUP ===")
logger.info("PORT=%s", os.environ.get("PORT", "NOT SET"))
logger.info("BOT_TOKEN set: %s", bool(os.environ.get("BOT_TOKEN")))
logger.info("FRAGMENT_API_KEY set: %s", bool(os.environ.get("FRAGMENT_API_KEY")))
logger.info("FRAGMENT_API_BASE=%s", os.environ.get("FRAGMENT_API_BASE", "NOT SET"))
logger.info("===============")


async def start_api_server():
    """Start aiohttp API server"""
    from api.server import create_app
    port = int(os.environ.get("PORT") or os.environ.get("API_PORT") or 8080)
    host = os.environ.get("API_HOST", "0.0.0.0")
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("API server started on %s:%s", host, port)
    return runner


async def main():
    # Start API server first (Railway needs port open to mark deploy as success)
    runner = await start_api_server()

    # Initialize Telethon gift sender (if credentials provided)
    logger.info(f"API_ID check: {config.API_ID}, API_HASH check: {bool(config.API_HASH)}")
    
    if config.API_ID and config.API_HASH:
        try:
            from services.telethon_client import init_gift_sender
            session = config.TELETHON_SESSION_STRING or config.SESSION_NAME
            logger.info(f"Initializing Telethon with session type: {'string' if config.TELETHON_SESSION_STRING else 'file'}")
            await init_gift_sender(
                config.API_ID,
                config.API_HASH,
                session,
                config.PHONE_NUMBER if config.PHONE_NUMBER else None
            )
            logger.info("Telethon gift sender initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Telethon: {e}")
            logger.warning("Gift sending will not be available")
    else:
        logger.warning(f"Telethon not configured: API_ID={config.API_ID}, API_HASH={'set' if config.API_HASH else 'not set'}")

    # Initialize bot
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Add access control middleware
    dp.update.middleware(AccessControlMiddleware())
    logger.info("Access control middleware enabled - only @StarPayUzAdmin can use the bot")

    dp.include_router(admin.router)   # Admin first — to prevent /admin being caught by start.router
    dp.include_router(start.router)
    dp.include_router(webapp.router)
    dp.include_router(shop.router)
    dp.include_router(balance.router)
    dp.include_router(profile.router)

    await database.init_db()
    logger.info("Database initialized, bot starting...")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Cleanup
        from services.telethon_client import stop_gift_sender
        await stop_gift_sender()
        await bot.session.close()
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
