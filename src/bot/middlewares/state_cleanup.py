from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject
from loguru import logger


class StateCleanupMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text:
            menu_buttons = [
                "➕ Добавить товар",
                "📦 Мои товары",
                "💎 Мой профиль",
                "⭐️ Баланс Stars",
            ]
            if event.text in menu_buttons:
                state: FSMContext = data["state"]
                current_state = await state.get_state()
                if current_state:
                    logger.debug(
                        f"Clearing state {current_state} for user {event.from_user.id if event.from_user else 'unknown'}"
                    )
                    await state.clear()

        return await handler(event, data)
