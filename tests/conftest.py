
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from src.db.models.models import Plan


@pytest_asyncio.fixture(scope="function")
async def db_session():
    # Use SQLite in-memory for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Seed initial plans
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        free_plan = Plan(
            id=1, name="Free", stars_price=0, max_products=5, check_interval_minutes=60
        )
        pro_plan = Plan(
            id=2, name="Pro", stars_price=100, max_products=50, check_interval_minutes=5
        )
        session.add(free_plan)
        session.add(pro_plan)
        await session.commit()

    async with Session() as session:
        yield session

    await engine.dispose()
