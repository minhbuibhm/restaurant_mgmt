from datetime import datetime

from sqlalchemy import Integer, String, Float, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    current_stock: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    min_threshold: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class InventoryLog(Base):
    __tablename__ = "inventory_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(Integer, nullable=False)
    change_amount: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
