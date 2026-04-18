from fastapi import HTTPException

from app.models.order import Order, OrderItemStatus, OrderStatus


class OrderTransitionPolicy:
    """Encapsulates allowed order status transitions."""

    valid_transitions: dict[OrderStatus, set[OrderStatus]] = {
        OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
        OrderStatus.CONFIRMED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
        OrderStatus.PREPARING: {OrderStatus.READY},
        OrderStatus.READY: {OrderStatus.SERVED},
        OrderStatus.SERVED: set(),
        OrderStatus.CANCELLED: set(),
    }

    def apply(self, order: Order, new_status: OrderStatus) -> None:
        allowed = self.valid_transitions.get(order.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from '{order.status.value}' to '{new_status.value}'",
            )

        order.update_status(new_status)
        if new_status == OrderStatus.CANCELLED:
            order.cancel_open_items()


class OrderItemTransitionPolicy:
    """Encapsulates allowed kitchen item status transitions."""

    valid_transitions: dict[OrderItemStatus, set[OrderItemStatus]] = {
        OrderItemStatus.QUEUED: {OrderItemStatus.COOKING, OrderItemStatus.CANCELLED},
        OrderItemStatus.COOKING: {OrderItemStatus.DONE},
        OrderItemStatus.DONE: set(),
        OrderItemStatus.CANCELLED: set(),
    }

    def validate(self, current_status: OrderItemStatus, new_status: OrderItemStatus) -> None:
        allowed = self.valid_transitions.get(current_status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition item from '{current_status.value}' to '{new_status.value}'",
            )
