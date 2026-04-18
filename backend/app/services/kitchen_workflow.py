from app.models.order import Order, OrderItem, OrderItemStatus, OrderStatus
from app.services.order_policy import OrderItemTransitionPolicy


class KitchenWorkflow:
    """Coordinates item cooking progression and parent order synchronization."""

    def __init__(self, item_policy: OrderItemTransitionPolicy | None = None) -> None:
        self.item_policy = item_policy or OrderItemTransitionPolicy()

    def advance_item_status(self, item: OrderItem, new_status: OrderItemStatus) -> None:
        self.item_policy.validate(item.status, new_status)
        if new_status == OrderItemStatus.DONE:
            item.mark_as_completed()
            return
        item.status = new_status

    def sync_order_status(self, order: Order, items: list[OrderItem]) -> None:
        statuses = {item.status for item in items}

        if statuses and all(
            status in (OrderItemStatus.DONE, OrderItemStatus.CANCELLED)
            for status in statuses
        ):
            order.update_status(OrderStatus.READY)
        elif OrderItemStatus.COOKING in statuses:
            order.update_status(OrderStatus.PREPARING)
