from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    percent_off: Mapped[int]
    active: Mapped[bool] = mapped_column(default=True)
    min_subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    usage_limit: Mapped[int | None]
    used_count: Mapped[int] = mapped_column(default=0)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime)

    orders: Mapped[list["Order"]] = relationship(back_populates="coupon")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    coupon_id: Mapped[int | None] = mapped_column(ForeignKey("coupons.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    shipping_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="orders")
    coupon: Mapped[Coupon | None] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    payment: Mapped["Payment | None"] = relationship(back_populates="order", uselist=False)
    shipment: Mapped["Shipment | None"] = relationship(back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), index=True)
    quantity: Mapped[int]
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    order: Mapped[Order] = relationship(back_populates="items")
    variant: Mapped["ProductVariant"] = relationship()


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    provider_reference: Mapped[str | None] = mapped_column(String(80), unique=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    order: Mapped[Order] = relationship(back_populates="payment")


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    carrier: Mapped[str] = mapped_column(String(60))
    tracking_code: Mapped[str | None] = mapped_column(String(80), unique=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    order: Mapped[Order] = relationship(back_populates="shipment")
