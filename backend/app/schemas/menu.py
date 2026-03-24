from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None

    model_config = {"from_attributes": True}


class MenuItemCreate(BaseModel):
    name: str
    description: str | None = None
    price: float
    category_id: int
    is_available: bool = True
    prep_time_minutes: int = 10
    image_url: str | None = None


class MenuItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    category_id: int | None = None
    is_available: bool | None = None
    prep_time_minutes: int | None = None
    image_url: str | None = None


class MenuItemResponse(BaseModel):
    id: int
    name: str
    description: str | None
    price: float
    category_id: int
    is_available: bool
    prep_time_minutes: int
    image_url: str | None

    model_config = {"from_attributes": True}
