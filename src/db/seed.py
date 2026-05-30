import asyncio

from sqlmodel import select

from src.db.models.models import Plan
from src.db.session import async_session


async def seed_plans():
    async with async_session() as session:
        # Check if plans already exist
        statement = select(Plan)
        result = await session.execute(statement)
        if result.first():
            print("Plans already seeded.")
            return

        free_plan = Plan(
            name="Free", stars_price=0, max_products=1, check_interval_minutes=240
        )
        pro_plan = Plan(
            name="Pro",
            stars_price=50,  # Example price in Stars
            max_products=20,
            check_interval_minutes=15,
        )

        session.add(free_plan)
        session.add(pro_plan)
        # await session.commit() # session.commit() is handled by async_session if used as a context manager with our get_session, but here we call it manually
        await session.commit()
        print("Plans seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed_plans())
