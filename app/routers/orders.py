from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.order import OrderRepository
from app.schemas.order import (
    CouponCreate,
    CouponRead,
    OrderCreate,
    OrderRead,
    PaymentCreate,
    ShipmentCreate,
    TransitionRequest,
)
from app.services.order import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])
coupon_router = APIRouter(prefix="/coupons", tags=["coupons"])


@coupon_router.post("", response_model=CouponRead, status_code=201)
def create_coupon(data: CouponCreate, db: Session = Depends(get_db)) -> CouponRead:
    return OrderService(db).create_coupon(data)


@router.post("", response_model=OrderRead, status_code=201)
def create_order(data: OrderCreate, db: Session = Depends(get_db)) -> OrderRead:
    return OrderService(db).create_order(data)


@router.get("", response_model=list[OrderRead])
def list_orders(
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[OrderRead]:
    return OrderRepository(db).list_orders(status=status, limit=limit, offset=offset)


@router.post("/{order_id}/transition", response_model=OrderRead)
def transition_order(order_id: int, data: TransitionRequest, db: Session = Depends(get_db)) -> OrderRead:
    return OrderService(db).transition(order_id, data.status)


@router.post("/{order_id}/payment", response_model=OrderRead)
def approve_payment(order_id: int, data: PaymentCreate, db: Session = Depends(get_db)) -> OrderRead:
    return OrderService(db).approve_payment(order_id, data)


@router.post("/{order_id}/shipment", response_model=OrderRead)
def create_shipment(order_id: int, data: ShipmentCreate, db: Session = Depends(get_db)) -> OrderRead:
    return OrderService(db).create_shipment(order_id, data)
