import asyncio
from typing import Any, Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiohttp import ClientSession
from aiohttp_socks import ProxyConnector
from loguru import logger

from src.bot.handlers.admin import router as admin_router
from src.bot.handlers.basic import router as basic_router
from src.bot.handlers.payments import router as payments_router
from src.bot.handlers.product import router as product_router
from src.bot.middlewares.db import DatabaseMiddleware
from src.bot.middlewares.state_cleanup import StateCleanupMiddleware
from src.core.config import settings
from src.core.logger import setup_logging


class UniversalProxySession(AiohttpSession):
    """
    Custom AiohttpSession that handles both HTTP and SOCKS5 proxies correctly.
    """

    def __init__(self, proxy_url: str, **kwargs: Any):
        super().__init__(**kwargs)
        self.proxy_url = proxy_url

    async def create_session(self) -> ClientSession:
        if self._session is None or self._session.closed:
            if self.proxy_url.startswith("socks"):
                # SOCKS proxies require a special connector
                connector = ProxyConnector.from_url(self.proxy_url)
                self._session = ClientSession(connector=connector)
                logger.debug("Created ClientSession with SOCKS connector")
            else:
                # For HTTP, we let the parent class handle it via the 'proxy' attribute
                self.proxy = self.proxy_url
                return await super().create_session()
        return self._session


async def main():
    setup_logging()

    session: Optional[AiohttpSession] = None
    if settings.PROXY_URL:
        session = UniversalProxySession(proxy_url=settings.PROXY_URL)
        logger.info(f"Using proxy: {settings.PROXY_URL}")

    bot = Bot(
        token=settings.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Register middlewares
    dp.update.outer_middleware(DatabaseMiddleware())
    dp.message.outer_middleware(StateCleanupMiddleware())

    # Register routers
    dp.include_router(admin_router)
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
