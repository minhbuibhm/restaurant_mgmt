from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.menu import MenuItem
from app.models.order import Order, OrderItem, OrderStatus, OrderItemStatus
from app.models.table import Table, TableStatus
from app.schemas.order import OrderCreate

# ── Status state machine ──
# Defines valid transitions: current_status -> set of allowed next statuses
VALID_ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.SERVED},
    OrderStatus.SERVED: set(),
    OrderStatus.CANCELLED: set(),
}


async def create_order(data: OrderCreate, db: AsyncSession) -> Order:
    """Validate inputs, calculate total, persist order + items."""
    # Validate table exists
    table = await db.get(Table, data.table_id)
    if not table:
        raise HTTPException(status_code=400, detail="Table not found")

    # Validate all menu items exist and are available
    item_ids = [i.menu_item_id for i in data.items]
    result = await db.execute(select(MenuItem).where(MenuItem.id.in_(item_ids)))
    menu_items = {mi.id: mi for mi in result.scalars().all()}

    for item in data.items:
        mi = menu_items.get(item.menu_item_id)
        if not mi:
            raise HTTPException(status_code=400, detail=f"Menu item {item.menu_item_id} not found")
        if not mi.is_available:
            raise HTTPException(status_code=400, detail=f"Menu item '{mi.name}' is not available")

    # Calculate total
    total = sum(menu_items[i.menu_item_id].price * i.quantity for i in data.items)

    # Create order
    order = Order(
        table_id=data.table_id,
        notes=data.notes,
        total_amount=total,
        status=OrderStatus.PENDING,
    )
    db.add(order)
    await db.flush()  # get order.id

    # Create order items
    for item in data.items:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item.menu_item_id,
            quantity=item.quantity,
            notes=item.notes,
            status=OrderItemStatus.QUEUED,
        )
        db.add(order_item)

    # Mark table as occupied
    table.status = TableStatus.OCCUPIED

    await db.commit()
    return await get_order(order.id, db)


async def get_order(order_id: int, db: AsyncSession) -> Order:
    """Fetch order with eager-loaded items and their menu item details."""
    stmt = (
        select(Order)
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
    """List orders with optional filters."""
    stmt = select(Order).options(selectinload(Order.items).selectinload(OrderItem.menu_item))
    if table_id is not None:
        stmt = stmt.where(Order.table_id == table_id)
    if status is not None:
        stmt = stmt.where(Order.status == status)
    stmt = stmt.order_by(Order.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_order_status(order_id: int, new_status: OrderStatus, db: AsyncSession) -> Order:
    """Transition order status following the state machine."""
    order = await get_order(order_id, db)
    allowed = VALID_ORDER_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{order.status.value}' to '{new_status.value}'",
        )
    order.status = new_status

    # When order is confirmed, mark items as ready for kitchen (they stay queued)
    # When order is cancelled, cancel all non-done items
    if new_status == OrderStatus.CANCELLED:
        for item in order.items:
            if item.status not in (OrderItemStatus.DONE, OrderItemStatus.CANCELLED):
                item.status = OrderItemStatus.CANCELLED

    await db.commit()
    await db.refresh(order)
    return order


async def cancel_order(order_id: int, db: AsyncSession) -> Order:
    """Cancel order — only allowed from pending or confirmed."""
    return await update_order_status(order_id, OrderStatus.CANCELLED, db)
