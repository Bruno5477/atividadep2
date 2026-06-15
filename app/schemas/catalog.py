from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = None


class CategoryRead(CategoryCreate):
    id: int

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    category_id: int
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=5)
    franchise: str = Field(min_length=2, max_length=80)


class ProductRead(ProductCreate):
    id: int
    active: bool

    model_config = {"from_attributes": True}


class VariantCreate(BaseModel):
    product_id: int
    sku: str = Field(min_length=3, max_length=40)
    name: str = Field(min_length=2, max_length=80)
    price: Decimal = Field(gt=0)
    stock_quantity: int = Field(ge=0)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.strip().upper()


class VariantRead(BaseModel):
    id: int
    product_id: int
    sku: str
    name: str
    price: Decimal
    stock_quantity: int
    reserved_quantity: int
    active: bool

    model_config = {"from_attributes": True}


class StockAdjust(BaseModel):
    quantity_delta: int
    reason: str = Field(min_length=3, max_length=40)

    @field_validator("quantity_delta")
    @classmethod
    def cannot_be_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("quantity_delta nao pode ser zero")
        return value
