from pydantic import BaseModel

from app.models.order import OrderItemStatus


class KitchenQueueItem(BaseModel):
    """Rich view of an order item for the KDS display."""
    order_item_id: int
    order_id: int
    table_number: int
    dish_name: str
    quantity: int
    category: str
    status: OrderItemStatus
    notes: str | None
    priority_score: float
    wait_time_seconds: float
    prep_time_minutes: int


class KitchenItemStatusUpdate(BaseModel):
    status: OrderItemStatus


class StationLoad(BaseModel):
    station: str
    active_items: int
    queued_items: int
