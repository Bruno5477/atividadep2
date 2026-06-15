from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app import models  # noqa: F401


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def store(client: TestClient) -> dict[str, int]:
    category = client.post("/catalog/categories", json={"name": "Figures"}).json()
    product = client.post(
        "/catalog/products",
        json={
            "category_id": category["id"],
            "name": "Naruto Uzumaki Figure",
            "description": "Colecionavel oficial de mesa",
            "franchise": "Naruto",
        },
    ).json()
    variant = client.post(
        "/catalog/variants",
        json={
            "product_id": product["id"],
            "sku": "nar-fig-01",
            "name": "Standard",
            "price": "120.00",
            "stock_quantity": 2,
        },
    ).json()
    customer = client.post(
        "/customers",
        json={
            "name": "Bruno",
            "email": "bruno@example.com",
            "city": "Sao Paulo",
            "state": "sp",
        },
    ).json()
    return {
        "category_id": category["id"],
        "product_id": product["id"],
        "variant_id": variant["id"],
        "customer_id": customer["id"],
    }
