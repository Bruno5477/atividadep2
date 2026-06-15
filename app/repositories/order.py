from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Coupon, Order


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_order(self, order_id: int) -> Order | None:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.payment), selectinload(Order.shipment))
        )
        return self.db.scalar(stmt)

    def list_orders(self, status: str | None, limit: int, offset: int) -> list[Order]:
        stmt = select(Order).options(selectinload(Order.items)).order_by(Order.id.desc())
        if status:
            stmt = stmt.where(Order.status == status)
        return list(self.db.scalars(stmt.offset(offset).limit(limit)))

    def get_coupon(self, code: str) -> Coupon | None:
        return self.db.scalar(select(Coupon).where(Coupon.code == code))
