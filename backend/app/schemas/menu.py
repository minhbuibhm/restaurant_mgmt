from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None

    model_config = {"from_attributes": True}


class DishCreate(BaseModel):
    name: str
    description: str | None = None
    price: float
    category_id: int
    is_available: bool = True
    average_prep_time: int = Field(default=10, alias="prep_time_minutes")
    image_url: str | None = None

    model_config = {"populate_by_name": True}


class DishUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    category_id: int | None = None
    is_available: bool | None = None
    average_prep_time: int | None = Field(default=None, alias="prep_time_minutes")
    image_url: str | None = None

    model_config = {"populate_by_name": True}


class DishResponse(BaseModel):
    id: int
    name: str
    description: str | None
    price: float
    category_id: int
    is_available: bool
    average_prep_time: int = Field(alias="prep_time_minutes")
    image_url: str | None

    model_config = {"from_attributes": True, "populate_by_name": True}


# Backward-compatible aliases preserving the existing API contract.
MenuItemCreate = DishCreate
MenuItemUpdate = DishUpdate
MenuItemResponse = DishResponse
