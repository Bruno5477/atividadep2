from fastapi.testclient import TestClient


def create_order(client: TestClient, store: dict[str, int], quantity: int = 1) -> dict:
    response = client.post(
        "/orders",
        json={
            "customer_id": store["customer_id"],
            "items": [{"variant_id": store["variant_id"], "quantity": quantity}],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_order_calculates_totals(client: TestClient, store: dict[str, int]) -> None:
    order = create_order(client, store)

    assert order["subtotal"] == "120.00"
    assert order["shipping_total"] == "18.90"
    assert order["grand_total"] == "138.90"
    assert order["status"] == "draft"


def test_product_list_supports_pagination_and_filter(client: TestClient, store: dict[str, int]) -> None:
    response = client.get("/catalog/products?limit=10&offset=0&franchise=Naruto&active=true")

    assert response.status_code == 200
    assert response.json()[0]["id"] == store["product_id"]


def test_confirm_order_reserves_stock(client: TestClient, store: dict[str, int]) -> None:
    order = create_order(client, store, quantity=2)

    response = client.post(f"/orders/{order['id']}/transition", json={"status": "confirmed"})

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"


def test_confirm_order_rejects_insufficient_stock(client: TestClient, store: dict[str, int]) -> None:
    first = create_order(client, store, quantity=2)
    second = create_order(client, store, quantity=1)
    assert client.post(f"/orders/{first['id']}/transition", json={"status": "confirmed"}).status_code == 200

    response = client.post(f"/orders/{second['id']}/transition", json={"status": "confirmed"})

    assert response.status_code == 409
    assert response.json()["error"] == "INSUFFICIENT_STOCK"


def test_invalid_state_transition_is_rejected(client: TestClient, store: dict[str, int]) -> None:
    order = create_order(client, store)

    response = client.post(f"/orders/{order['id']}/transition", json={"status": "delivered"})

    assert response.status_code == 409
    assert response.json()["error"] == "INVALID_ORDER_TRANSITION"


def test_payment_requires_confirmed_order(client: TestClient, store: dict[str, int]) -> None:
    order = create_order(client, store)

    response = client.post(f"/orders/{order['id']}/payment", json={"amount": order["grand_total"]})

    assert response.status_code == 409
    assert response.json()["error"] == "ORDER_NOT_PAYABLE"


def test_payment_amount_must_match_total(client: TestClient, store: dict[str, int]) -> None:
    order = create_order(client, store)
    client.post(f"/orders/{order['id']}/transition", json={"status": "confirmed"})

    response = client.post(f"/orders/{order['id']}/payment", json={"amount": "1.00"})

    assert response.status_code == 422
    assert response.json()["error"] == "PAYMENT_AMOUNT_MISMATCH"


def test_paid_order_can_be_shipped(client: TestClient, store: dict[str, int]) -> None:
    order = create_order(client, store)
    client.post(f"/orders/{order['id']}/transition", json={"status": "confirmed"})
    paid = client.post(f"/orders/{order['id']}/payment", json={"amount": order["grand_total"]}).json()

    response = client.post(
        f"/orders/{paid['id']}/shipment",
        json={"carrier": "Correios", "tracking_code": "BR123"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "shipped"


def test_coupon_applies_discount_and_free_shipping(client: TestClient, store: dict[str, int]) -> None:
    client.post(
        "/coupons",
        json={"code": "AKATSUKI10", "percent_off": 10, "min_subtotal": "100.00", "usage_limit": 1},
    )

    response = client.post(
        "/orders",
        json={
            "customer_id": store["customer_id"],
            "coupon_code": "akatsuki10",
            "items": [{"variant_id": store["variant_id"], "quantity": 2}],
        },
    )

    assert response.status_code == 201
    assert response.json()["discount_total"] == "24.00"
    assert response.json()["shipping_total"] == "18.90"


def test_coupon_minimum_subtotal_is_enforced(client: TestClient, store: dict[str, int]) -> None:
    client.post(
        "/coupons",
        json={"code": "HOKAGE50", "percent_off": 50, "min_subtotal": "200.00"},
    )

    response = client.post(
        "/orders",
        json={
            "customer_id": store["customer_id"],
            "coupon_code": "HOKAGE50",
            "items": [{"variant_id": store["variant_id"], "quantity": 1}],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"] == "COUPON_MIN_SUBTOTAL"


def test_stock_adjust_cannot_go_below_reserved(client: TestClient, store: dict[str, int]) -> None:
    order = create_order(client, store, quantity=2)
    client.post(f"/orders/{order['id']}/transition", json={"status": "confirmed"})

    response = client.post(
        f"/catalog/variants/{store['variant_id']}/stock",
        json={"quantity_delta": -1, "reason": "inventory_count"},
    )

    assert response.status_code == 409
    assert response.json()["error"] == "STOCK_BELOW_RESERVED"
