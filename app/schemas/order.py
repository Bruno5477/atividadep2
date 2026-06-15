from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


class CouponCreate(BaseModel):
    code: str = Field(min_length=3, max_length=30)
    percent_off: int = Field(ge=1, le=80)
    min_subtotal: Decimal = Field(default=Decimal("0"), ge=0)
    usage_limit: int | None = Field(default=None, gt=0)
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def valid_window(self) -> "CouponCreate":
        if self.valid_from and self.valid_until and self.valid_from >= self.valid_until:
            raise ValueError("valid_from deve ser anterior a valid_until")
        return self


class CouponRead(CouponCreate):
    id: int
    active: bool
    used_count: int

    model_config = {"from_attributes": True}


class OrderItemCreate(BaseModel):
    variant_id: int
    quantity: int = Field(gt=0, le=20)


class OrderCreate(BaseModel):
    customer_id: int
    items: list[OrderItemCreate] = Field(min_length=1)
    coupon_code: str | None = None

    @field_validator("coupon_code")
    @classmethod
    def normalize_coupon(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value


class OrderItemRead(BaseModel):
    id: int
    variant_id: int
    quantity: int
    unit_price: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class OrderRead(BaseModel):
    id: int
    customer_id: int
    status: str
    subtotal: Decimal
    discount_total: Decimal
    shipping_total: Decimal
    grand_total: Decimal
    items: list[OrderItemRead]

    model_config = {"from_attributes": True}


class TransitionRequest(BaseModel):
    status: str = Field(min_length=3, max_length=20)


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    provider_reference: str | None = Field(default=None, max_length=80)


class ShipmentCreate(BaseModel):
    carrier: str = Field(min_length=2, max_length=60)
    tracking_code: str | None = Field(default=None, max_length=80)
