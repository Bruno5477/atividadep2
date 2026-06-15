from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.models.audit import AuditLog
from app.models.catalog import ProductVariant
from app.models.customer import Customer
from app.models.order import Coupon, Order, OrderItem, Payment, Shipment
from app.repositories.order import OrderRepository
from app.schemas.order import CouponCreate, OrderCreate, PaymentCreate, ShipmentCreate

ALLOWED_TRANSITIONS = {
    "draft": {"confirmed", "canceled"},
    "confirmed": {"paid", "canceled"},
    "paid": {"shipped", "canceled"},
    "shipped": {"delivered"},
    "delivered": set(),
    "canceled": set(),
}
TERMINAL_STATUSES = {"delivered", "canceled"}


class OrderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = OrderRepository(db)

    def create_coupon(self, data: CouponCreate) -> Coupon:
        coupon = Coupon(**data.model_dump())
        self.db.add(coupon)
        self.db.commit()
        self.db.refresh(coupon)
        return coupon

    def create_order(self, data: OrderCreate) -> Order:
        if not self.db.get(Customer, data.customer_id):
            raise DomainError("CUSTOMER_NOT_FOUND", "Cliente informado nao existe.", 404)
        order = Order(customer_id=data.customer_id, status="draft")
        self.db.add(order)
        self.db.flush()

        subtotal = Decimal("0")
        for item_data in data.items:
            variant = self.db.get(ProductVariant, item_data.variant_id)
            if not variant or not variant.active or not variant.product.active:
                raise DomainError(
                    "VARIANT_NOT_AVAILABLE",
                    "Variante inexistente ou indisponivel para venda.",
                    404,
                    {"variant_id": item_data.variant_id},
                )
            line_total = self._money(variant.price * item_data.quantity)
            subtotal += line_total
            self.db.add(
                OrderItem(
                    order_id=order.id,
                    variant_id=variant.id,
                    quantity=item_data.quantity,
                    unit_price=variant.price,
                    line_total=line_total,
                )
            )

        order.subtotal = self._money(subtotal)
        order.coupon = self._validate_coupon(data.coupon_code, order.subtotal)
        order.discount_total = self._discount(order.subtotal, order.coupon)
        order.shipping_total = self._shipping_for(order.subtotal - order.discount_total)
        order.grand_total = self._money(order.subtotal - order.discount_total + order.shipping_total)

        self.db.commit()
        return self.repo.get_order(order.id) or order

    def transition(self, order_id: int, next_status: str) -> Order:
        order = self._order_or_404(order_id)
        if next_status not in ALLOWED_TRANSITIONS[order.status]:
            raise DomainError(
                "INVALID_ORDER_TRANSITION",
                "Transicao de estado nao permitida para o pedido.",
                409,
                {"current_status": order.status, "requested_status": next_status},
            )
        if next_status == "confirmed":
            self._reserve_stock(order)
            if order.coupon:
                order.coupon.used_count += 1
        if next_status == "canceled":
            self._release_stock_if_needed(order)
        order.status = next_status
        self._audit(order.id, "transition", {"to": next_status})
        self.db.commit()
        return self.repo.get_order(order.id) or order

    def approve_payment(self, order_id: int, data: PaymentCreate) -> Order:
        order = self._order_or_404(order_id)
        if order.status != "confirmed":
            raise DomainError(
                "ORDER_NOT_PAYABLE",
                "Apenas pedidos confirmados podem receber pagamento.",
                409,
                {"current_status": order.status},
            )
        if data.amount != order.grand_total:
            raise DomainError(
                "PAYMENT_AMOUNT_MISMATCH",
                "Valor do pagamento deve ser igual ao total do pedido.",
                422,
                {"expected": str(order.grand_total), "received": str(data.amount)},
            )
        order.payment = Payment(amount=data.amount, status="approved", provider_reference=data.provider_reference)
        order.status = "paid"
        self._audit(order.id, "payment_approved", {"amount": str(data.amount)})
        self.db.commit()
        return self.repo.get_order(order.id) or order

    def create_shipment(self, order_id: int, data: ShipmentCreate) -> Order:
        order = self._order_or_404(order_id)
        if order.status != "paid":
            raise DomainError(
                "ORDER_NOT_SHIPPABLE",
                "Apenas pedidos pagos podem ser enviados.",
                409,
                {"current_status": order.status},
            )
        order.shipment = Shipment(status="posted", carrier=data.carrier, tracking_code=data.tracking_code)
        order.status = "shipped"
        self._commit_reserved_stock(order)
        self._audit(order.id, "shipment_created", data.model_dump())
        self.db.commit()
        return self.repo.get_order(order.id) or order

    def _validate_coupon(self, code: str | None, subtotal: Decimal) -> Coupon | None:
        if not code:
            return None
        coupon = self.repo.get_coupon(code)
        now = datetime.utcnow()
        if not coupon or not coupon.active:
            raise DomainError("COUPON_INVALID", "Cupom inexistente ou inativo.", 422, {"code": code})
        if coupon.valid_from and now < coupon.valid_from:
            raise DomainError("COUPON_NOT_STARTED", "Cupom ainda nao esta vigente.", 422, {"code": code})
        if coupon.valid_until and now > coupon.valid_until:
            raise DomainError("COUPON_EXPIRED", "Cupom expirado.", 422, {"code": code})
        if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
            raise DomainError("COUPON_USAGE_LIMIT", "Cupom atingiu o limite de uso.", 422, {"code": code})
        if subtotal < coupon.min_subtotal:
            raise DomainError(
                "COUPON_MIN_SUBTOTAL",
                "Subtotal do pedido nao atinge o minimo exigido pelo cupom.",
                422,
                {"min_subtotal": str(coupon.min_subtotal), "subtotal": str(subtotal)},
            )
        return coupon

    def _reserve_stock(self, order: Order) -> None:
        for item in order.items:
            variant = self.db.get(ProductVariant, item.variant_id)
            available = variant.stock_quantity - variant.reserved_quantity
            if item.quantity > available:
                raise DomainError(
                    "INSUFFICIENT_STOCK",
                    "Estoque disponivel insuficiente para confirmar o pedido.",
                    409,
                    {"variant_id": item.variant_id, "available": available, "requested": item.quantity},
                )
            variant.reserved_quantity += item.quantity

    def _release_stock_if_needed(self, order: Order) -> None:
        if order.status in {"confirmed", "paid"}:
            for item in order.items:
                variant = self.db.get(ProductVariant, item.variant_id)
                variant.reserved_quantity -= item.quantity

    def _commit_reserved_stock(self, order: Order) -> None:
        for item in order.items:
            variant = self.db.get(ProductVariant, item.variant_id)
            variant.reserved_quantity -= item.quantity
            variant.stock_quantity -= item.quantity

    def _order_or_404(self, order_id: int) -> Order:
        order = self.repo.get_order(order_id)
        if not order:
            raise DomainError("ORDER_NOT_FOUND", "Pedido nao encontrado.", 404)
        return order

    def _discount(self, subtotal: Decimal, coupon: Coupon | None) -> Decimal:
        if not coupon:
            return Decimal("0")
        return self._money(subtotal * Decimal(coupon.percent_off) / Decimal("100"))

    def _shipping_for(self, amount_after_discount: Decimal) -> Decimal:
        if amount_after_discount >= Decimal("250"):
            return Decimal("0")
        return Decimal("18.90")

    def _money(self, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _audit(self, entity_id: int, action: str, payload: dict) -> None:
        self.db.add(AuditLog(entity="order", entity_id=entity_id, action=action, payload=payload))
