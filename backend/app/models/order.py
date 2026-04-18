import enum
from datetime import datetime

from sqlalchemy import Integer, ForeignKey, Enum, DateTime, Text, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    SERVED = "served"
    CANCELLED = "cancelled"


class OrderItemStatus(str, enum.Enum):
    QUEUED = "queued"
    COOKING = "cooking"
    DONE = "done"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False
    )
    total_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")

    def add_item(
        self,
        dish_id: int,
        quantity: int = 1,
        notes: str | None = None,
        status: "OrderItemStatus" = OrderItemStatus.QUEUED,
    ) -> "OrderItem":
        return OrderItem(
            order_id=self.id,
            menu_item_id=dish_id,
            quantity=quantity,
            notes=notes,
            status=status,
        )

    def calculate_total(
        self,
        dishes_by_id: dict[int, "Dish"],
        items: list["OrderItem"] | None = None,
    ) -> float:
        source_items = items if items is not None else self.items
        self.total_amount = sum(
            dishes_by_id[item.menu_item_id].price * item.quantity
            for item in source_items
        )
        return self.total_amount

    def update_status(self, new_status: OrderStatus) -> None:
        self.status = new_status

    def cancel_open_items(self) -> None:
        for item in self.items:
            if item.status not in (OrderItemStatus.DONE, OrderItemStatus.CANCELLED):
                item.status = OrderItemStatus.CANCELLED


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[OrderItemStatus] = mapped_column(
        Enum(OrderItemStatus), default=OrderItemStatus.QUEUED, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="items")
    menu_item: Mapped["Dish"] = relationship()

    def update_priority(self, score: float) -> float:
        return score

    def mark_as_completed(self) -> None:
        self.status = OrderItemStatus.DONE

    @property
    def customer_note(self) -> str | None:
        return self.notes

    @customer_note.setter
    def customer_note(self, value: str | None) -> None:
        self.notes = value

    @property
    def dish_id(self) -> int:
        return self.menu_item_id

    @dish_id.setter
    def dish_id(self, value: int) -> None:
        self.menu_item_id = value

    @property
    def dish(self):
        return self.menu_item

    @dish.setter
    def dish(self, value) -> None:
        self.menu_item = value
