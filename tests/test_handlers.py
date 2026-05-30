from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from aiogram.types import Message

from src.bot.handlers.product import cmd_my_products
from src.db.models.models import Product, User


@pytest.fixture
def mock_user():
    return User(id=123, username="testuser", plan_id=1)


@pytest.mark.asyncio
async def test_cmd_my_products_empty(db_session, mock_user):
    # Mock message
    message = AsyncMock(spec=Message)
    message.answer = AsyncMock()

    await cmd_my_products(message, mock_user, db_session)

    # Since there are no products, it should show the empty message
    message.answer.assert_called_once()
    args, _ = message.answer.call_args
    assert "У тебя пока нет отслеживаемых товаров" in args[0]


@pytest.mark.asyncio
async def test_cmd_my_products_with_items(db_session, mock_user):
    # Add a product
    product = Product(
        user_id=mock_user.id,
        url="https://wb.ru/1",
        title="Item 1",
        current_price=Decimal("100"),
        target_price=Decimal("90"),
    )
    db_session.add(product)
    await db_session.commit()

    # Mock message
    message = AsyncMock(spec=Message)
    message.answer = AsyncMock()

    await cmd_my_products(message, mock_user, db_session)

    message.answer.assert_called_once()
    args, kwargs = message.answer.call_args
    assert "Твои отслеживаемые товары" in args[0]
    assert "reply_markup" in kwargs
