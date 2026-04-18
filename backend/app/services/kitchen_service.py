from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import OrderItemStatus
from app.schemas.kitchen import KitchenQueueItem, StationLoad
from app.services.contracts import (
    IEventPublisher,
    IKitchenRepository,
    IPriorityStrategy,
    NullEventPublisher,
    SqlAlchemyKitchenRepository,
)
from app.services.kitchen_queue import KitchenQueue
from app.services.kitchen_workflow import KitchenWorkflow
from app.services.priority_scorer import PriorityScorer


class KitchenService:
    def __init__(
        self,
        repo: IKitchenRepository,
        strategy: IPriorityStrategy | None = None,
        publisher: IEventPublisher | None = None,
        workflow: KitchenWorkflow | None = None,
    ) -> None:
        self.repo = repo
        self.strategy = strategy or PriorityScorer()
        self.publisher = publisher or NullEventPublisher()
        self.workflow = workflow or KitchenWorkflow()

    async def handle_order_created(self, order_id: int) -> None:
        await self.publisher.publish({"type": "order_created", "order_id": order_id})

    async def get_station_load(self) -> list[StationLoad]:
        rows = await self.repo.get_station_load()
        return [
            StationLoad(station=station, active_items=active_items, queued_items=queued_items)
            for station, active_items, queued_items in rows
        ]

    async def process_queue(self) -> list[KitchenQueueItem]:
        station_loads = await self.get_station_load()
        station_load_map = {load.station: load.active_items for load in station_loads}
        kitchen_queue = KitchenQueue(strategy=self.strategy)

        for ticket in await self.repo.get_pending_tickets():
            kitchen_queue.enqueue(ticket, station_load_map.get(ticket.station, 0))

        ranked_tickets = kitchen_queue.reorder()
        return [
            KitchenQueueItem(
                order_item_id=ticket.order_item.id,
                order_id=ticket.order.id,
                table_number=ticket.table_number,
                dish_name=ticket.dish.name,
                quantity=ticket.order_item.quantity,
                category=ticket.station,
                status=ticket.order_item.status,
                notes=ticket.order_item.notes,
                priority_score=ticket.priority,
                wait_time_seconds=round(ticket.wait_time_seconds, 1),
                prep_time_minutes=ticket.dish.average_prep_time,
            )
            for ticket in ranked_tickets
        ]

    async def advance_item_status(self, item_id: int, new_status: OrderItemStatus) -> dict:
        order_item = await self.repo.get_order_item(item_id)
        if not order_item:
            raise HTTPException(status_code=404, detail="Order item not found")

        self.workflow.advance_item_status(order_item, new_status)
        await self.repo.flush()

        order = await self.repo.get_order(order_item.order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        order_items = await self.repo.list_order_items(order.id)
        self.workflow.sync_order_status(order, order_items)

        await self.repo.commit()
        return {
            "order_item_id": item_id,
            "status": order_item.status.value,
            "order_status": order.status.value,
        }


def _build_service(db: AsyncSession) -> KitchenService:
    return KitchenService(SqlAlchemyKitchenRepository(db))


async def get_station_load(db: AsyncSession) -> list[StationLoad]:
    return await _build_service(db).get_station_load()


async def get_kitchen_queue(db: AsyncSession) -> list[KitchenQueueItem]:
    return await _build_service(db).process_queue()


async def advance_item_status(
    item_id: int,
    new_status: OrderItemStatus,
    db: AsyncSession,
) -> dict:
    return await _build_service(db).advance_item_status(item_id, new_status)
