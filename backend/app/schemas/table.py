from pydantic import BaseModel

from app.models.table import TableStatus


class TableCreate(BaseModel):
    number: int
    capacity: int
    status: TableStatus = TableStatus.AVAILABLE
    qr_code: str | None = None


class TableUpdate(BaseModel):
    capacity: int | None = None
    status: TableStatus | None = None
    qr_code: str | None = None


class TableResponse(BaseModel):
    id: int
    number: int
    capacity: int
    status: TableStatus
    qr_code: str | None

    model_config = {"from_attributes": True}
