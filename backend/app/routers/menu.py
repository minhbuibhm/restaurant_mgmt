from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.menu import Category, MenuItem
from app.models.user import UserRole
from app.schemas.menu import (
    CategoryCreate, CategoryResponse,
    MenuItemCreate, MenuItemUpdate, MenuItemResponse,
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

@router.post("/items", response_model=MenuItemResponse, status_code=201, dependencies=MANAGER_ONLY)
async def create_menu_item(data: MenuItemCreate, db: AsyncSession = Depends(get_db)):
    category = await db.get(Category, data.category_id)
    if not category:
        raise HTTPException(status_code=400, detail="Category not found")
    item = MenuItem(**data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/items", response_model=list[MenuItemResponse])
async def list_menu_items(
    category_id: int | None = Query(None),
    available: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MenuItem)
    if category_id is not None:
        stmt = stmt.where(MenuItem.category_id == category_id)
    if available is not None:
        stmt = stmt.where(MenuItem.is_available == available)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/items/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(item_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item


@router.patch("/items/{item_id}", response_model=MenuItemResponse, dependencies=MANAGER_ONLY)
async def update_menu_item(item_id: int, data: MenuItemUpdate, db: AsyncSession = Depends(get_db)):
    item = await db.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item
