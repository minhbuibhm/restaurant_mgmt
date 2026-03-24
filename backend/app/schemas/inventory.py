from datetime import datetime

from pydantic import BaseModel


class IngredientCreate(BaseModel):
    name: str
    unit: str
    current_stock: float = 0.0
    min_threshold: float = 0.0


class IngredientUpdate(BaseModel):
    current_stock: float | None = None
    min_threshold: float | None = None


class IngredientResponse(BaseModel):
    id: int
    name: str
    unit: str
    current_stock: float
    min_threshold: float

    model_config = {"from_attributes": True}


class InventoryLogResponse(BaseModel):
    id: int
    ingredient_id: int
    change_amount: float
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
