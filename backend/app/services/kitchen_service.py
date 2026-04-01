from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.menu import MenuItem, Category
from app.models.order import Order, OrderItem, OrderItemStatus, OrderStatus
from app.models.table import Table
from app.schemas.kitchen import KitchenQueueItem, StationLoad

# ── Item status state machine ──
VALID_ITEM_TRANSITIONS: dict[OrderItemStatus, set[OrderItemStatus]] = {
    OrderItemStatus.QUEUED: {OrderItemStatus.COOKING, OrderItemStatus.CANCELLED},
    OrderItemStatus.COOKING: {OrderItemStatus.DONE},
    OrderItemStatus.DONE: set(),
    OrderItemStatus.CANCELLED: set(),
}

# ── Priority scoring weights (docs/design.md §8.4) ──
WEIGHT_WAIT_TIME = 0.5
WEIGHT_COMPLEXITY = 0.3
WEIGHT_STATION_LOAD = 0.2
MAX_PREP_TIME = 60  # minutes, used for normalization


def calculate_priority_score(
    wait_seconds: float,
    prep_time_minutes: int,
    station_active_count: int,
) -> float:
    """
    Priority score: higher = should be cooked sooner.

    Factors (per docs/design.md §8.4):
    - wait_time: longer wait -> higher priority
    - complexity: simpler dishes -> higher priority (faster throughput)
    - station_load: less loaded station -> higher priority (available capacity)
    """
    # Normalize wait time (cap at 30 min = 1800s for scoring)
    wait_score = min(wait_seconds / 1800.0, 1.0) * 100

    # Complexity: inverse — simpler dishes score higher
    complexity_score = (1 - min(prep_time_minutes / MAX_PREP_TIME, 1.0)) * 100

    # Station load: inverse — less loaded stations score higher
    load_score = max(0, (1 - station_active_count / 10.0)) * 100

    return round(
        WEIGHT_WAIT_TIME * wait_score
        + WEIGHT_COMPLEXITY * complexity_score
        + WEIGHT_STATION_LOAD * load_score,
        1,
    )


async def get_station_load(db: AsyncSession) -> list[StationLoad]:
    """Count active (cooking) and queued items grouped by category (category = station)."""
    stmt = (
        select(
            Category.name.label("station"),
            func.count(case((OrderItem.status == OrderItemStatus.COOKING, 1))).label("active_items"),
            func.count(case((OrderItem.status == OrderItemStatus.QUEUED, 1))).label("queued_items"),
        )
        .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
        .join(Category, MenuItem.category_id == Category.id)
        .where(OrderItem.status.in_([OrderItemStatus.QUEUED, OrderItemStatus.COOKING]))
        .group_by(Category.name)
    )
    result = await db.execute(stmt)
    return [StationLoad(station=row.station, active_items=row.active_items, queued_items=row.queued_items) for row in result.all()]


async def get_kitchen_queue(db: AsyncSession) -> list[KitchenQueueItem]:
    """Return all queued/cooking items, enriched and sorted by priority score."""
    # Get station loads for scoring
    loads = await get_station_load(db)
    load_map = {s.station: s.active_items for s in loads}

    # Fetch active order items with joins
    stmt = (
        select(OrderItem, Order, MenuItem, Category, Table)
        .join(Order, OrderItem.order_id == Order.id)
        .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
        .join(Category, MenuItem.category_id == Category.id)
        .join(Table, Order.table_id == Table.id)
        .where(OrderItem.status.in_([OrderItemStatus.QUEUED, OrderItemStatus.COOKING]))
        .where(Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING]))
    )
    result = await db.execute(stmt)
    rows = result.all()

    now = datetime.now(timezone.utc)
    queue_items = []
    for order_item, order, menu_item, category, table in rows:
        wait_seconds = (now - order.created_at).total_seconds()
        station_load = load_map.get(category.name, 0)
        score = calculate_priority_score(wait_seconds, menu_item.prep_time_minutes, station_load)

        queue_items.append(KitchenQueueItem(
            order_item_id=order_item.id,
            order_id=order.id,
            table_number=table.number,
            dish_name=menu_item.name,
            quantity=order_item.quantity,
            category=category.name,
            status=order_item.status,
            notes=order_item.notes,
            priority_score=score,
            wait_time_seconds=round(wait_seconds, 1),
            prep_time_minutes=menu_item.prep_time_minutes,
        ))

    # Sort by priority score descending (highest priority first)
    queue_items.sort(key=lambda x: x.priority_score, reverse=True)
    return queue_items


async def advance_item_status(
    item_id: int,
    new_status: OrderItemStatus,
    db: AsyncSession,
) -> KitchenQueueItem | dict:
    """Advance an order item's cooking status and sync parent order status."""
    order_item = await db.get(OrderItem, item_id)
    if not order_item:
        raise HTTPException(status_code=404, detail="Order item not found")

    allowed = VALID_ITEM_TRANSITIONS.get(order_item.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition item from '{order_item.status.value}' to '{new_status.value}'",
        )

    order_item.status = new_status
    await db.flush()

    # Sync parent order status based on item states
    order = await db.get(Order, order_item.order_id)
    stmt = select(OrderItem).where(OrderItem.order_id == order.id)
    result = await db.execute(stmt)
    all_items = result.scalars().all()
    await _sync_order_status(order, all_items)

    await db.commit()
    return {"order_item_id": item_id, "status": new_status.value, "order_status": order.status.value}


async def _sync_order_status(order: Order, items: list[OrderItem]) -> None:
    """Auto-advance order status based on item statuses.

    - Any item cooking -> order is preparing
    - All items done -> order is ready
    """
    statuses = {item.status for item in items}

    if all(s in (OrderItemStatus.DONE, OrderItemStatus.CANCELLED) for s in statuses):
        order.status = OrderStatus.READY
    elif OrderItemStatus.COOKING in statuses:
        order.status = OrderStatus.PREPARING
