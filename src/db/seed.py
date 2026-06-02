import asyncio

from loguru import logger
from sqlmodel import select

from src.db.models.models import Plan
from src.db.session import async_session


async def seed_plans():
    async with async_session() as session:
        # Define the plans we want to have
        plans_data = [
            {
                "name": "Free",
                "stars_price": 0,
                "max_products": 1,
                "check_interval_minutes": 240,
            },
            {
                "name": "Pro",
                "stars_price": 50,
                "max_products": 20,
                "check_interval_minutes": 60,
            },
        ]

        logger.info("Starting plans seeding/updating...")

        for data in plans_data:
            # Check if plan with this name exists
            statement = select(Plan).where(Plan.name == data["name"])
            result = await session.execute(statement)
            existing_plan = result.scalar_one_or_none()

            if existing_plan:
                # Update existing plan's interval and other fields
                existing_plan.check_interval_minutes = data["check_interval_minutes"]
                existing_plan.max_products = data["max_products"]
                existing_plan.stars_price = data["stars_price"]
                logger.info(
                    f"Plan '{data['name']}' updated (interval: {data['check_interval_minutes']}m)."
                )
            else:
                # Create new plan
                new_plan = Plan(**data)
                session.add(new_plan)
                logger.success(f"Plan '{data['name']}' created.")

        await session.commit()
        logger.success("Plans seeding/updating completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_plans())
