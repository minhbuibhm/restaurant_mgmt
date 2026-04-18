from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["Dish"]] = relationship(back_populates="category")


class Dish(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    prep_time_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    category: Mapped["Category"] = relationship(back_populates="items")

    @property
    def average_prep_time(self) -> int:
        return self.prep_time_minutes

    @average_prep_time.setter
    def average_prep_time(self, value: int) -> None:
        self.prep_time_minutes = value


# Backward-compatible alias for existing routers/schemas and ORM references.
MenuItem = Dish
