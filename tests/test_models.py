from decimal import Decimal

import pytest
from sqlmodel import select

from src.db.models.models import Plan, Product, User


@pytest.mark.asyncio
async def test_create_user_and_product(db_session):
    # Plan is already seeded in conftest.py
    user = User(id=123, username="testuser", plan_id=1)
    db_session.add(user)
    await db_session.commit()

    product = Product(
        user_id=123,
        url="https://wb.ru/123",
        title="Test Item",
        current_price=Decimal("100.00"),
        target_price=Decimal("90.00"),
        is_favorite=True,
        threshold=Decimal("5.00"),
    )
    db_session.add(product)
    await db_session.commit()

    # Verify
    stmt = select(Product).where(Product.user_id == 123)
    result = await db_session.execute(stmt)
    p = result.scalar_one()

    assert p.title == "Test Item"
    assert p.is_favorite is True
    assert p.threshold == Decimal("5.00")


@pytest.mark.asyncio
async def test_plan_limits(db_session):
    stmt = select(Plan).where(Plan.name == "Free")
    result = await db_session.execute(stmt)
    plan = result.scalar_one()
    assert plan.max_products == 5
