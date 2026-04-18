from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.menu import Category, Dish
from app.models.user import UserRole
from app.schemas.menu import (
    CategoryCreate, CategoryResponse,
    DishCreate, DishResponse, DishUpdate,
)

router = APIRouter(prefix="/menu", tags=["menu"])

MANAGER_ONLY = [Depends(require_role(UserRole.MANAGER))]

# ── Categories ──

@router.post("/categories", response_model=CategoryResponse, status_code=201, dependencies=MANAGER_ONLY)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    category = Category(**data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category))
    return result.scalars().all()


# ── Menu Items ──

@router.post("/items", response_model=DishResponse, status_code=201, dependencies=MANAGER_ONLY)
async def create_dish(data: DishCreate, db: AsyncSession = Depends(get_db)):
    category = await db.get(Category, data.category_id)
    if not category:
        raise HTTPException(status_code=400, detail="Category not found")
    dish = Dish(**data.model_dump())
    db.add(dish)
    await db.commit()
    await db.refresh(dish)
    return dish


@router.get("/items", response_model=list[DishResponse])
async def list_dishes(
    category_id: int | None = Query(None),
    available: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Dish)
    if category_id is not None:
        stmt = stmt.where(Dish.category_id == category_id)
    if available is not None:
        stmt = stmt.where(Dish.is_available == available)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/items/{item_id}", response_model=DishResponse)
async def get_dish(item_id: int, db: AsyncSession = Depends(get_db)):
    dish = await db.get(Dish, item_id)
    if not dish:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return dish


@router.patch("/items/{item_id}", response_model=DishResponse, dependencies=MANAGER_ONLY)
async def update_dish(item_id: int, data: DishUpdate, db: AsyncSession = Depends(get_db)):
    dish = await db.get(Dish, item_id)
    if not dish:
        raise HTTPException(status_code=404, detail="Menu item not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(dish, key, value)
    await db.commit()
    await db.refresh(dish)
    return dish
