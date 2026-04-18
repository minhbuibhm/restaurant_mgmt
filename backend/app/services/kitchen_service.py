from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.menu import Category, Dish
from app.models.order import Order, OrderItem, OrderItemStatus, OrderStatus
from app.models.table import Table
from app.schemas.kitchen import KitchenQueueItem, StationLoad
from app.services.kitchen_queue import KitchenQueue
from app.services.kitchen_workflow import KitchenWorkflow

kitchen_workflow = KitchenWorkflow()


async def get_station_load(db: AsyncSession) -> list[StationLoad]:
    stmt = (
        select(
            Category.name.label("station"),
            func.count(case((OrderItem.status == OrderItemStatus.COOKING, 1))).label("active_items"),
            func.count(case((OrderItem.status == OrderItemStatus.QUEUED, 1))).label("queued_items"),
        )
        .join(Dish, OrderItem.menu_item_id == Dish.id)
        .join(Category, Dish.category_id == Category.id)
        .where(OrderItem.status.in_([OrderItemStatus.QUEUED, OrderItemStatus.COOKING]))
        .group_by(Category.name)
    )
    result = await db.execute(stmt)
    return [
        StationLoad(
            station=row.station,
            active_items=row.active_items,
            queued_items=row.queued_items,
        )
        for row in result.all()
    ]


async def get_kitchen_queue(db: AsyncSession) -> list[KitchenQueueItem]:
    station_loads = await get_station_load(db)
    station_load_map = {load.station: load.active_items for load in station_loads}
    kitchen_queue = KitchenQueue()

    stmt = (
        select(OrderItem, Order, Dish, Category, Table)
        .join(Order, OrderItem.order_id == Order.id)
        .join(Dish, OrderItem.menu_item_id == Dish.id)
        .join(Category, Dish.category_id == Category.id)
        .join(Table, Order.table_id == Table.id)
        .where(OrderItem.status.in_([OrderItemStatus.QUEUED, OrderItemStatus.COOKING]))
        .where(Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING]))
    )
    result = await db.execute(stmt)
    queue_rows = result.all()

    now = datetime.now(timezone.utc)
    for order_item, order, dish, category, table in queue_rows:
        wait_seconds = (now - order.created_at).total_seconds()
        kitchen_queue.add_item(
            KitchenQueueItem(
                order_item_id=order_item.id,
                order_id=order.id,
                table_number=table.number,
                dish_name=dish.name,
                quantity=order_item.quantity,
                category=category.name,
                status=order_item.status,
                notes=order_item.notes,
                priority_score=0.0,
                wait_time_seconds=round(wait_seconds, 1),
                prep_time_minutes=dish.average_prep_time,
            ),
            wait_seconds=wait_seconds,
            prep_time_minutes=dish.average_prep_time,
            station_active_count=station_load_map.get(category.name, 0),
        )

    return kitchen_queue.re_rank_by_priority()


async def advance_item_status(
    item_id: int,
    new_status: OrderItemStatus,
    db: AsyncSession,
) -> dict:
    order_item = await db.get(OrderItem, item_id)
    if not order_item:
        raise HTTPException(status_code=404, detail="Order item not found")

    kitchen_workflow.advance_item_status(order_item, new_status)
    await db.flush()

    order = await db.get(Order, order_item.order_id)
    result = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    kitchen_workflow.sync_order_status(order, result.scalars().all())

    await db.commit()
    return {
        "order_item_id": item_id,
        "status": order_item.status.value,
        "order_status": order.status.value,
    }
