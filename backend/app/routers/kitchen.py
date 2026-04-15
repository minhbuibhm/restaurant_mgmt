from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import UserRole
from app.schemas.kitchen import KitchenQueueItem, KitchenItemStatusUpdate, StationLoad
from app.services import kitchen_service

router = APIRouter(
    prefix="/kitchen",
    tags=["kitchen"],
    dependencies=[Depends(require_role(UserRole.CHEF, UserRole.MANAGER))],
)


@router.get("/queue", response_model=list[KitchenQueueItem])
async def get_kitchen_queue(db: AsyncSession = Depends(get_db)):
    return await kitchen_service.get_kitchen_queue(db)


@router.patch("/items/{item_id}/status")
async def update_item_status(
    item_id: int,
    data: KitchenItemStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await kitchen_service.advance_item_status(item_id, data.status, db)


@router.get("/stations/load", response_model=list[StationLoad])
async def get_station_load(db: AsyncSession = Depends(get_db)):
    return await kitchen_service.get_station_load(db)
