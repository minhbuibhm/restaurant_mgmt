from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.menu import Dish
from app.models.order import Order, OrderItem, OrderItemStatus, OrderStatus
from app.models.table import Table, TableStatus
from app.schemas.order import OrderCreate
from app.services.order_policy import OrderTransitionPolicy

order_policy = OrderTransitionPolicy()


async def create_order(data: OrderCreate, db: AsyncSession) -> Order:
    table = await _get_table_or_400(data.table_id, db)
    dishes = await _get_available_dishes(data, db)

    order = Order(
        table_id=data.table_id,
        notes=data.notes,
        status=OrderStatus.PENDING,
    )
    db.add(order)
    await db.flush()

    order_items: list[OrderItem] = []
    for item in data.items:
        dish_id = item.menu_item_id
        order_item = order.add_item(
            dish_id=dish_id,
            quantity=item.quantity,
            notes=item.notes,
            status=OrderItemStatus.QUEUED,
        )
        db.add(order_item)
        order_item.dish = dishes[dish_id]
        order_items.append(order_item)

    order.calculate_total(dishes, order_items)
    table.status = TableStatus.OCCUPIED

    await db.commit()
    return await get_order(order.id, db)


async def get_order(order_id: int, db: AsyncSession) -> Order:
    stmt = (
        select(Order)
        .execution_options(populate_existing=True)
        .options(selectinload(Order.items).selectinload(OrderItem.menu_item))
        .where(Order.id == order_id)
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


async def list_orders(
    db: AsyncSession,
    table_id: int | None = None,
    status: OrderStatus | None = None,
) -> list[Order]:
    stmt = (
        select(Order)
        .execution_options(populate_existing=True)
        .options(selectinload(Order.items).selectinload(OrderItem.menu_item))
    )

    if table_id is not None:
        stmt = stmt.where(Order.table_id == table_id)
    if status is not None:
        stmt = stmt.where(Order.status == status)

    stmt = stmt.order_by(Order.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_order_status(order_id: int, new_status: OrderStatus, db: AsyncSession) -> Order:
    order = await get_order(order_id, db)
    order_policy.apply(order, new_status)

    await db.commit()
    await db.refresh(order)
    return order


async def cancel_order(order_id: int, db: AsyncSession) -> Order:
    return await update_order_status(order_id, OrderStatus.CANCELLED, db)


async def _get_table_or_400(table_id: int, db: AsyncSession) -> Table:
    table = await db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=400, detail="Table not found")
    return table


async def _get_available_dishes(data: OrderCreate, db: AsyncSession) -> dict[int, Dish]:
    dish_ids = [item.menu_item_id for item in data.items]
    result = await db.execute(select(Dish).where(Dish.id.in_(dish_ids)))
    dishes = {dish.id: dish for dish in result.scalars().all()}

    for item in data.items:
        dish_id = item.menu_item_id
        dish = dishes.get(dish_id)
        if not dish:
            raise HTTPException(
                status_code=400,
                detail=f"Dish {dish_id} not found",
            )
        if not dish.is_available:
            raise HTTPException(
                status_code=400,
                detail=f"Dish '{dish.name}' is not available",
            )

    return dishes
