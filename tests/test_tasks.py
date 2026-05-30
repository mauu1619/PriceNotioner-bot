from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from src.db.models.models import Product, User
from src.tasks.price_check import check_all_prices


@pytest.mark.asyncio
async def test_price_check_notifies_on_drop(db_session, httpx_mock):
    # Setup: Create a user and a product with a target price
    user = User(id=111, username="notify_user", plan_id=1)
    db_session.add(user)

    # Set last_checked_at to far in the past to trigger check
    past_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)

    product = Product(
        user_id=111,
        url="12345",
        title="Test Item",
        current_price=Decimal("1000.00"),
        target_price=Decimal("900.00"),
        is_favorite=False,
        threshold=Decimal("0.00"),
        last_notified_price=Decimal("1000.00"),
        last_checked_at=past_time,
    )
    db_session.add(product)
    await db_session.commit()

    # Mock WB API to return a price below target
    mock_data = {
        "products": [
            {
                "name": "Test Item",
                "sizes": [{"price": {"product": 85000}}],  # 850.00 RUB
            }
        ]
    }
    httpx_mock.add_response(
        url="https://card.wb.ru/cards/v4/detail?appType=1&curr=rub&dest=-1257786&nm=12345",
        json=mock_data,
    )

    # Patch Bot.send_message to track notifications
    with patch("src.tasks.price_check.Bot") as MockBot:
        mock_bot_instance = MockBot.return_value
        mock_bot_instance.send_message = AsyncMock()
        mock_bot_instance.session.close = AsyncMock()

        # Run the task
        with patch("src.tasks.price_check.async_session") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = db_session
            await check_all_prices()

        # Verify notification was sent
        assert mock_bot_instance.send_message.called
        args, kwargs = mock_bot_instance.send_message.call_args
        assert kwargs["chat_id"] == 111
        assert "Цена снизилась" in kwargs["text"]
        # In current implementation, price in text is 850 (without .00)
        assert "850" in kwargs["text"]


@pytest.mark.asyncio
async def test_price_check_favorite_threshold(db_session, httpx_mock):
    # Setup: Favorite product with threshold
    user = User(id=222, username="fav_user", plan_id=1)
    db_session.add(user)

    past_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)

    product = Product(
        user_id=222,
        url="54321",
        title="Fav Item",
        current_price=Decimal("1000.00"),
        target_price=Decimal("500.00"),
        is_favorite=True,
        threshold=Decimal("50.00"),
        last_notified_price=Decimal("1000.00"),
        last_checked_at=past_time,
    )
    db_session.add(product)
    await db_session.commit()

    # Case 1: Small change (below threshold) -> No notification
    httpx_mock.add_response(
        url="https://card.wb.ru/cards/v4/detail?appType=1&curr=rub&dest=-1257786&nm=54321",
        json={
            "products": [{"name": "Fav Item", "sizes": [{"price": {"product": 98000}}]}]
        },  # 980.00
    )

    with patch("src.tasks.price_check.Bot") as MockBot:
        mock_bot_instance = MockBot.return_value
        mock_bot_instance.send_message = AsyncMock()
        mock_bot_instance.session.close = AsyncMock()

        with patch("src.tasks.price_check.async_session") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = db_session
            await check_all_prices()

        assert not mock_bot_instance.send_message.called

    # Case 2: Big change (above threshold) -> Notification
    product.last_checked_at = past_time
    await db_session.commit()

    httpx_mock.add_response(
        url="https://card.wb.ru/cards/v4/detail?appType=1&curr=rub&dest=-1257786&nm=54321",
        json={
            "products": [
                {"name": "Fav Item", "sizes": [{"price": {"product": 110000}}]}
            ]
        },  # 1100.00 (+100)
    )

    with patch("src.tasks.price_check.Bot") as MockBot:
        mock_bot_instance = MockBot.return_value
        mock_bot_instance.send_message = AsyncMock()
        mock_bot_instance.session.close = AsyncMock()

        with patch("src.tasks.price_check.async_session") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = db_session
            await check_all_prices()

        assert mock_bot_instance.send_message.called
        assert (
            "Избранный товар изменился"
            in mock_bot_instance.send_message.call_args[1]["text"]
        )
