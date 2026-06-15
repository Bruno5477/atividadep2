from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.catalog import CatalogRepository
from app.schemas.catalog import (
    CategoryCreate,
    CategoryRead,
    ProductCreate,
    ProductRead,
    StockAdjust,
    VariantCreate,
    VariantRead,
)
from app.services.catalog import CatalogService

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.post("/categories", response_model=CategoryRead, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)) -> CategoryRead:
    return CatalogService(db).create_category(data)


@router.post("/products", response_model=ProductRead, status_code=201)
def create_product(data: ProductCreate, db: Session = Depends(get_db)) -> ProductRead:
    return CatalogService(db).create_product(data)


@router.get("/products", response_model=list[ProductRead])
def list_products(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    franchise: str | None = None,
    active: bool | None = None,
    db: Session = Depends(get_db),
) -> list[ProductRead]:
    return CatalogRepository(db).list_products(limit=limit, offset=offset, franchise=franchise, active=active)


@router.post("/variants", response_model=VariantRead, status_code=201)
def create_variant(data: VariantCreate, db: Session = Depends(get_db)) -> VariantRead:
    return CatalogService(db).create_variant(data)


@router.post("/variants/{variant_id}/stock", response_model=VariantRead)
def adjust_stock(variant_id: int, data: StockAdjust, db: Session = Depends(get_db)) -> VariantRead:
    return CatalogService(db).adjust_stock(variant_id, data)
