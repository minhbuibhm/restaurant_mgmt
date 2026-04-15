from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.order import OrderStatus
from app.models.user import UserRole
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    order = await order_service.create_order(data, db)
    return order


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    table_id: int | None = Query(None),
    status: OrderStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await order_service.list_orders(db, table_id=table_id, status=status)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    return await order_service.get_order(order_id, db)


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    dependencies=[Depends(require_role(UserRole.WAITER, UserRole.MANAGER))],
)
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await order_service.update_order_status(order_id, data.status, db)


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    dependencies=[Depends(require_role(UserRole.MANAGER))],
)
async def cancel_order(order_id: int, db: AsyncSession = Depends(get_db)):
    return await order_service.cancel_order(order_id, db)
