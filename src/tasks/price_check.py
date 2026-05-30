import asyncio
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from loguru import logger
from sqlmodel import select

from src.core.config import settings
from src.core.logger import setup_logging
from src.db.models.models import Plan, Product, User
from src.db.session import async_session
from src.parsers.wildberries import get_wb_product
from src.tasks.broker import broker

setup_logging()


@broker.task(schedule=[{"cron": "* * * * *"}])
async def check_all_prices():
    """
    Asynchronous Taskiq task that checks prices for all eligible products.
    Runs every minute.
    """
    logger.info("Starting periodic price check...")

    session_bot = None
    if settings.PROXY_URL:
        session_bot = AiohttpSession(proxy=settings.PROXY_URL)

    bot = Bot(
        token=settings.BOT_TOKEN,
        session=session_bot,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    now = datetime.utcnow()

    async with async_session() as db:
        # Fetch all products with their user's plan to determine interval
        # Using a join to get product, user, and plan together
        stmt = (
            select(Product, User, Plan)
            .join(User, Product.user_id == User.id)  # type: ignore
            .join(Plan, User.plan_id == Plan.id)  # type: ignore
        )

        result = await db.execute(stmt)
        records = result.all()

        logger.info(f"Found {len(records)} products in database.")

        for product, user, plan in records:
            # Determine if this product needs checking based on plan interval
            interval = timedelta(minutes=plan.check_interval_minutes)

            if product.last_checked_at and (now - product.last_checked_at) < interval:
                logger.debug(f"Skipping product {product.id} (next check not due yet)")
                continue

            logger.info(f"Checking price for product {product.id} (URL: {product.url})")

            try:
                parsed_data = await get_wb_product(product.url)

                if not parsed_data:
                    logger.warning(f"Failed to parse data for product {product.id}")
                    # Update last_checked_at anyway to avoid spamming the parser
                    product.last_checked_at = now
                    await db.commit()
                    continue

                title, current_price, clean_url = parsed_data

                # Logic for notification
                notify = False
                last_notified = product.last_notified_price

                if product.is_favorite:
                    # Favorite: notify on any change >= threshold
                    if last_notified is None:
                        # First notification for favorite
                        notify = True
                    else:
                        diff = abs(current_price - last_notified)
                        if diff >= product.threshold:
                            notify = True
                else:
                    # Non-favorite: notify only when crossing target price
                    if current_price <= product.target_price:
                        if (
                            last_notified is None
                            or last_notified > product.target_price
                        ):
                            notify = True

                if notify:
                    logger.info(
                        f"Notification triggered for product {product.id}! Reason: {'Favorite change' if product.is_favorite else 'Target reached'}. Price: {current_price:f}"
                    )

                    try:
                        status_text = (
                            "⭐ <b>Избранный товар изменился!</b>"
                            if product.is_favorite
                            else "🎉 <b>Цена снизилась!</b>"
                        )

                        price_diff_text = ""
                        if last_notified:
                            diff = current_price - last_notified
                            if diff < 0:
                                price_diff_text = f" (📉 {abs(diff):f} ₽)"
                            else:
                                price_diff_text = f" (📈 {diff:f} ₽)"

                        await bot.send_message(
                            chat_id=user.id,
                            text=(
                                f"{status_text}\n\n"
                                f"Товар: <a href='{clean_url}'>{title}</a>\n"
                                f"Текущая цена: <b>{current_price:f} ₽</b>{price_diff_text}\n"
                                f"Предыдущая цена: {last_notified:f} ₽\n"
                                if last_notified
                                else ""
                                f"Желаемая цена: {product.target_price:f} ₽\n\n"
                                f"Успейте купить!"
                            ),
                            disable_web_page_preview=False,
                        )
                        product.last_notified_price = current_price
                    except Exception as e:
                        logger.error(
                            f"Failed to send notification to user {user.id}: {e}"
                        )

                # Update product in DB
                product.current_price = current_price
                product.title = title
                product.last_checked_at = now

                await db.commit()

                # Sleep briefly to avoid hitting rate limits
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error checking product {product.id}: {e}")

    await bot.session.close()
    logger.info("Finished periodic price check.")
