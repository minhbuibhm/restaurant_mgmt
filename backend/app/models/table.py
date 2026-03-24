import enum
from sqlalchemy import Integer, String, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TableStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[TableStatus] = mapped_column(
        Enum(TableStatus), default=TableStatus.AVAILABLE, nullable=False
    )
    qr_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
