from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as AiogramUser
from loguru import logger
from sqlmodel import select

from src.db.models.models import Plan, User
from src.db.session import async_session


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session() as session:
            data["db_session"] = session

            tg_user: AiogramUser | None = data.get("event_from_user")
            if tg_user:
                telegram_id = tg_user.id
                username = tg_user.username

                stmt = select(User).where(User.id == telegram_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    plan_stmt = select(Plan).where(Plan.name == "Free")
                    plan_result = await session.execute(plan_stmt)
                    free_plan = plan_result.scalar_one_or_none()
                    plan_id = (
                        int(free_plan.id)
                        if free_plan and free_plan.id is not None
                        else 1
                    )

                    user = User(id=telegram_id, username=username, plan_id=plan_id)
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)
                    logger.info(
                        f"Registered new user in DB: {telegram_id} (username: {username})"
                    )

                data["db_user"] = user

            return await handler(event, data)
