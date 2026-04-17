from datetime import datetime

from pydantic import BaseModel

from app.models.order import OrderStatus, OrderItemStatus
from app.schemas.menu import MenuItemResponse


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = 1
    notes: str | None = None


class OrderCreate(BaseModel):
    table_id: int
    notes: str | None = None
    items: list[OrderItemCreate]


class OrderItemResponse(BaseModel):
    id: int
    menu_item_id: int
    quantity: int
    status: OrderItemStatus
    notes: str | None
    menu_item: MenuItemResponse

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderResponse(BaseModel):
    id: int
    table_id: int
    status: OrderStatus
    total_amount: float
    notes: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []

    model_config = {"from_attributes": True}
