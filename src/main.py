import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from loguru import logger

from src.bot.handlers.basic import router as basic_router
from src.bot.handlers.payments import router as payments_router
from src.bot.handlers.product import router as product_router
from src.bot.middlewares.db import DatabaseMiddleware
from src.core.config import settings
from src.core.logger import setup_logging


async def main():
    setup_logging()

    session = None
    if settings.PROXY_URL:
        session = AiohttpSession(proxy=settings.PROXY_URL)

    bot = Bot(
        token=settings.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Register middlewares
    dp.update.outer_middleware(DatabaseMiddleware())

    # Register routers
    dp.include_router(basic_router)
    dp.include_router(product_router)
    dp.include_router(payments_router)

    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
