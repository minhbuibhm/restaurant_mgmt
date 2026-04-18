from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.menu import Dish
from app.models.order import Order, OrderItem, OrderItemStatus, OrderStatus
from app.models.table import Table


@dataclass
class OrderCreatedEvent:
    order_id: int
    table_id: int


@dataclass
class KitchenTicket:
    id: int
    order_item: OrderItem
    order: Order
    dish: Dish
    station: str
    table_number: int
    wait_time_seconds: float
    priority: float = 0.0

    def calculate_priority(self, strategy: "IPriorityStrategy", station_load: int) -> float:
        self.priority = strategy.calculate(self, station_load)
        return self.priority


class IOrderRepository(Protocol):
    async def get_table(self, table_id: int) -> Table | None: ...
    async def get_dishes(self, dish_ids: list[int]) -> dict[int, Dish]: ...
    async def add_order(self, order: Order) -> None: ...
    async def add_order_item(self, item: OrderItem) -> None: ...
    async def get_order(self, order_id: int) -> Order | None: ...
    async def list_orders(
        self,
        table_id: int | None = None,
        status: OrderStatus | None = None,
    ) -> list[Order]: ...
    async def commit(self) -> None: ...
    async def flush(self) -> None: ...
    async def refresh(self, order: Order) -> None: ...


class IKitchenRepository(Protocol):
    async def get_station_load(self) -> list[tuple[str, int, int]]: ...
    async def get_pending_tickets(self) -> list[KitchenTicket]: ...
    async def get_order_item(self, item_id: int) -> OrderItem | None: ...
    async def get_order(self, order_id: int) -> Order | None: ...
    async def list_order_items(self, order_id: int) -> list[OrderItem]: ...
    async def flush(self) -> None: ...
    async def commit(self) -> None: ...


class IEventPublisher(Protocol):
    async def publish(self, event: object) -> None: ...


class IPriorityStrategy(Protocol):
    def calculate(self, ticket: KitchenTicket, station_load: int) -> float: ...


class NullEventPublisher:
    async def publish(self, event: object) -> None:
        return None


class SqlAlchemyOrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_table(self, table_id: int) -> Table | None:
        return await self.db.get(Table, table_id)

    async def get_dishes(self, dish_ids: list[int]) -> dict[int, Dish]:
        from sqlalchemy import select

        result = await self.db.execute(select(Dish).where(Dish.id.in_(dish_ids)))
        return {dish.id: dish for dish in result.scalars().all()}

    async def add_order(self, order: Order) -> None:
        self.db.add(order)

    async def add_order_item(self, item: OrderItem) -> None:
        self.db.add(item)

    async def get_order(self, order_id: int) -> Order | None:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = (
            select(Order)
            .execution_options(populate_existing=True)
            .options(selectinload(Order.items).selectinload(OrderItem.menu_item))
            .where(Order.id == order_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_orders(
        self,
        table_id: int | None = None,
        status: OrderStatus | None = None,
    ) -> list[Order]:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

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
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def commit(self) -> None:
        await self.db.commit()

    async def flush(self) -> None:
        await self.db.flush()

    async def refresh(self, order: Order) -> None:
        await self.db.refresh(order)


class SqlAlchemyKitchenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_station_load(self) -> list[tuple[str, int, int]]:
        from sqlalchemy import case, func, select
        from app.models.menu import Category

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
        result = await self.db.execute(stmt)
        return [(row.station, row.active_items, row.queued_items) for row in result.all()]

    async def get_pending_tickets(self) -> list[KitchenTicket]:
        from datetime import datetime, timezone
        from sqlalchemy import select
        from app.models.menu import Category

        stmt = (
            select(OrderItem, Order, Dish, Category, Table)
            .join(Order, OrderItem.order_id == Order.id)
            .join(Dish, OrderItem.menu_item_id == Dish.id)
            .join(Category, Dish.category_id == Category.id)
            .join(Table, Order.table_id == Table.id)
            .where(OrderItem.status.in_([OrderItemStatus.QUEUED, OrderItemStatus.COOKING]))
            .where(Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING]))
        )
        result = await self.db.execute(stmt)
        now = datetime.now(timezone.utc)
        tickets: list[KitchenTicket] = []
        for order_item, order, dish, category, table in result.all():
            tickets.append(
                KitchenTicket(
                    id=order_item.id,
                    order_item=order_item,
                    order=order,
                    dish=dish,
                    station=category.name,
                    table_number=table.number,
                    wait_time_seconds=(now - order.created_at).total_seconds(),
                )
            )
        return tickets

    async def get_order_item(self, item_id: int) -> OrderItem | None:
        return await self.db.get(OrderItem, item_id)

    async def get_order(self, order_id: int) -> Order | None:
        return await self.db.get(Order, order_id)

    async def list_order_items(self, order_id: int) -> list[OrderItem]:
        from sqlalchemy import select

        result = await self.db.execute(select(OrderItem).where(OrderItem.order_id == order_id))
        return result.scalars().all()

    async def flush(self) -> None:
        await self.db.flush()

    async def commit(self) -> None:
        await self.db.commit()
