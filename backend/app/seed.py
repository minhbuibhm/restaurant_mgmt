"""Seed initial data for development. Idempotent — only seeds if DB is empty."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.menu import Category, MenuItem
from app.models.table import Table
from app.models.user import User, UserRole
from app.services.auth_service import hash_password


async def seed_if_empty() -> None:
    async with async_session() as db:
        # Check if any data exists — skip if already seeded
        result = await db.execute(select(Category).limit(1))
        if result.scalar_one_or_none() is not None:
            return

        await _seed(db)
        await db.commit()


async def _seed(db: AsyncSession) -> None:
    # Categories (double as kitchen stations)
    main = Category(name="main", description="Main dishes")
    drink = Category(name="drink", description="Beverages")
    dessert = Category(name="dessert", description="Desserts")
    db.add_all([main, drink, dessert])
    await db.flush()

    # Menu items (image_url sourced from TheMealDB / TheCocktailDB — see README)
    db.add_all([
        MenuItem(name="Grilled Salmon", description="Atlantic salmon with herbs", price=15.5,
                 category_id=main.id, prep_time_minutes=20,
                 image_url="https://www.themealdb.com/images/media/meals/1548772327.jpg"),
        MenuItem(name="Beef Steak", description="Ribeye, medium-rare", price=22.0,
                 category_id=main.id, prep_time_minutes=25,
                 image_url="https://www.themealdb.com/images/media/meals/vussxq1511882648.jpg"),
        MenuItem(name="Caesar Salad", description="Romaine, parmesan, croutons", price=8.5,
                 category_id=main.id, prep_time_minutes=5,
                 image_url="https://www.themealdb.com/images/media/meals/k29viq1585565980.jpg"),
        MenuItem(name="Lemonade", description="Fresh-squeezed", price=5.0,
                 category_id=drink.id, prep_time_minutes=3,
                 image_url="https://www.thecocktaildb.com/images/media/drink/b3n0ge1503565473.jpg"),
        MenuItem(name="Iced Coffee", description="Cold brew", price=4.5,
                 category_id=drink.id, prep_time_minutes=3,
                 image_url="https://www.thecocktaildb.com/images/media/drink/ytprxy1454513855.jpg"),
        MenuItem(name="Tiramisu", description="Classic Italian", price=7.0,
                 category_id=dessert.id, prep_time_minutes=2,
                 image_url="https://www.themealdb.com/images/media/meals/1549542877.jpg"),
    ])

    # Tables
    db.add_all([
        Table(number=1, capacity=2),
        Table(number=2, capacity=4),
        Table(number=3, capacity=4),
        Table(number=4, capacity=6),
        Table(number=5, capacity=8),
    ])

    # Users — password is the same as username for easy testing (dev only)
    db.add_all([
        User(username="manager", hashed_password=hash_password("manager"),
             full_name="Alice Manager", role=UserRole.MANAGER),
        User(username="chef", hashed_password=hash_password("chef"),
             full_name="Bob Chef", role=UserRole.CHEF),
        User(username="waiter", hashed_password=hash_password("waiter"),
             full_name="Carol Waiter", role=UserRole.WAITER),
    ])
