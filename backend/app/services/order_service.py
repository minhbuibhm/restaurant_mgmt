from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderItemStatus, OrderStatus
from app.models.table import TableStatus
from app.schemas.order import OrderCreate
from app.services.contracts import (
    IEventPublisher,
    IOrderRepository,
    NullEventPublisher,
    OrderCreatedEvent,
    SqlAlchemyOrderRepository,
)
from app.services.order_policy import OrderTransitionPolicy


class OrderService:
    def __init__(
        self,
        repo: IOrderRepository,
        publisher: IEventPublisher | None = None,
        policy: OrderTransitionPolicy | None = None,
    ) -> None:
        self.repo = repo
        self.publisher = publisher or NullEventPublisher()
        self.policy = policy or OrderTransitionPolicy()

    async def create_order(self, data: OrderCreate) -> Order:
        table = await self.repo.get_table(data.table_id)
        if not table:
            raise HTTPException(status_code=400, detail="Table not found")

        dish_ids = [item.menu_item_id for item in data.items]
        dishes = await self.repo.get_dishes(dish_ids)

        for item in data.items:
            dish_id = item.menu_item_id
            dish = dishes.get(dish_id)
            if not dish:
                raise HTTPException(status_code=400, detail=f"Dish {dish_id} not found")
            if not dish.is_available:
                raise HTTPException(status_code=400, detail=f"Dish '{dish.name}' is not available")

        order = Order(
            table_id=data.table_id,
            notes=data.notes,
            status=OrderStatus.PENDING,
        )
        await self.repo.add_order(order)
        await self.repo.flush()

        order_items: list[OrderItem] = []
        for item in data.items:
            dish_id = item.menu_item_id
            order_item = order.add_item(
                dish_id=dish_id,
                quantity=item.quantity,
                notes=item.notes,
                status=OrderItemStatus.QUEUED,
            )
            await self.repo.add_order_item(order_item)
            order_item.dish = dishes[dish_id]
            order_items.append(order_item)

        order.calculate_total(dishes, order_items)
        table.status = TableStatus.OCCUPIED

        await self.repo.commit()
        await self.publisher.publish(OrderCreatedEvent(order_id=order.id, table_id=order.table_id))
        created = await self.repo.get_order(order.id)
        if not created:
            raise HTTPException(status_code=404, detail="Order not found")
        return created

    async def get_order(self, order_id: int) -> Order:
        order = await self.repo.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    async def list_orders(
        self,
        table_id: int | None = None,
        status: OrderStatus | None = None,
    ) -> list[Order]:
        return await self.repo.list_orders(table_id=table_id, status=status)

    async def update_order_status(self, order_id: int, new_status: OrderStatus) -> Order:
        order = await self.get_order(order_id)
        self.policy.apply(order, new_status)
        await self.repo.commit()
        await self.repo.refresh(order)
        return order

    async def cancel_order(self, order_id: int) -> Order:
        return await self.update_order_status(order_id, OrderStatus.CANCELLED)


def _build_service(db: AsyncSession) -> OrderService:
    return OrderService(SqlAlchemyOrderRepository(db))


async def create_order(data: OrderCreate, db: AsyncSession) -> Order:
    return await _build_service(db).create_order(data)


async def get_order(order_id: int, db: AsyncSession) -> Order:
    return await _build_service(db).get_order(order_id)


async def list_orders(
    db: AsyncSession,
    table_id: int | None = None,
    status: OrderStatus | None = None,
) -> list[Order]:
    return await _build_service(db).list_orders(table_id=table_id, status=status)


async def update_order_status(order_id: int, new_status: OrderStatus, db: AsyncSession) -> Order:
    return await _build_service(db).update_order_status(order_id, new_status)


async def cancel_order(order_id: int, db: AsyncSession) -> Order:
    return await _build_service(db).cancel_order(order_id)
