"""Seed initial data for development. Idempotent — only seeds if DB is empty."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.menu import Category, MenuItem
from app.models.table import Table
from app.models.user import User, UserRole
from app.services.auth_service import hash_password

# Image URLs sourced from TheMealDB / TheCocktailDB (see updated.txt)
_IMG = {
    "light_food": "https://www.themealdb.com/images/media/meals/k29viq1585565980.jpg",
    "main_food":  "https://www.themealdb.com/images/media/meals/zadvgb1699012544.jpg",
    "iced_coffee":"https://www.thecocktaildb.com/images/media/drink/ytprxy1454513855.jpg",
    "drink":      "https://www.thecocktaildb.com/images/media/drink/b3n0ge1503565473.jpg",
    "dessert":    "https://www.themealdb.com/images/media/meals/1549542877.jpg",
}


async def seed_if_empty() -> None:
    async with async_session() as db:
        result = await db.execute(select(Category).limit(1))
        if result.scalar_one_or_none() is not None:
            return

        await _seed(db)
        await db.commit()


async def _seed(db: AsyncSession) -> None:
    # Categories
    khai_vi    = Category(name="Khai vi",    description="Các món khai vị")
    mon_chinh  = Category(name="Mon chinh",  description="Các món chính")
    do_uong    = Category(name="Do uong",    description="Đồ uống")
    trang_miem = Category(name="Trang miem", description="Tráng miệng")
    db.add_all([khai_vi, mon_chinh, do_uong, trang_miem])
    await db.flush()

    # Menu items
    db.add_all([
        # Khai vi
        MenuItem(name="Goi cuon",  description="Goi cuon tom thit",           price=45000, category_id=khai_vi.id,    prep_time_minutes=5,  image_url=_IMG["light_food"]),
        MenuItem(name="Cha gio",   description="Cha gio ran gion",             price=55000, category_id=khai_vi.id,    prep_time_minutes=8,  image_url=_IMG["light_food"]),
        MenuItem(name="Sup cua",   description="Sup cua bap",                  price=65000, category_id=khai_vi.id,    prep_time_minutes=10, image_url=_IMG["main_food"]),
        # Mon chinh
        MenuItem(name="Pho bo",         description="Pho bo truyen thong",          price=85000,  category_id=mon_chinh.id, prep_time_minutes=15, image_url=_IMG["main_food"]),
        MenuItem(name="Com tam suon bi", description="Com tam suon nuong, bi, cha",  price=75000,  category_id=mon_chinh.id, prep_time_minutes=12, image_url=_IMG["main_food"]),
        MenuItem(name="Bun bo Hue",      description="Bun bo cay dac trung Hue",     price=80000,  category_id=mon_chinh.id, prep_time_minutes=15, image_url=_IMG["main_food"]),
        MenuItem(name="Bo luc lac",      description="Bo luc lac chien bo",          price=195000, category_id=mon_chinh.id, prep_time_minutes=20, image_url=_IMG["main_food"]),
        # Do uong
        MenuItem(name="Ca phe sua da",   description="Ca phe Viet truyen thong",     price=35000, category_id=do_uong.id,    prep_time_minutes=5, image_url=_IMG["iced_coffee"]),
        MenuItem(name="Tra dao cam sa",  description="Tra dao tuoi mat lanh",        price=45000, category_id=do_uong.id,    prep_time_minutes=5, image_url=_IMG["drink"]),
        MenuItem(name="Sinh to bo",      description="Sinh to bo tuoi beo ngay",     price=55000, category_id=do_uong.id,    prep_time_minutes=7, image_url=_IMG["drink"]),
        MenuItem(name="Nuoc chanh muoi", description="Chanh tuoi muoi me",           price=30000, category_id=do_uong.id,    prep_time_minutes=3, image_url=_IMG["drink"]),
        # Trang miem
        MenuItem(name="Che ba mau",          description="Che ba mau dac trung Nam Bo",   price=35000, category_id=trang_miem.id, prep_time_minutes=5, image_url=_IMG["dessert"]),
        MenuItem(name="Banh flan ca ra men", description="Banh flan mem min voi ca phe",  price=40000, category_id=trang_miem.id, prep_time_minutes=3, image_url=_IMG["dessert"]),
        MenuItem(name="Kem dua",             description="Kem dua tuoi that",             price=45000, category_id=trang_miem.id, prep_time_minutes=3, image_url=_IMG["dessert"]),
    ])

    # Tables
    db.add_all([
        Table(number=1, capacity=2),
        Table(number=2, capacity=4),
        Table(number=3, capacity=4),
        Table(number=4, capacity=6),
        Table(number=5, capacity=8),
    ])

    # Users — password same as username for dev
    db.add_all([
        User(username="manager", hashed_password=hash_password("manager"),
             full_name="Alice Manager", role=UserRole.MANAGER),
        User(username="chef",    hashed_password=hash_password("chef"),
             full_name="Bob Chef",     role=UserRole.CHEF),
        User(username="waiter",  hashed_password=hash_password("waiter"),
             full_name="Carol Waiter", role=UserRole.WAITER),
    ])
