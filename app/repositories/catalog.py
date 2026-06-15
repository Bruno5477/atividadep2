from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Category, Product, ProductVariant
from app.repositories.base import Repository


class CatalogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.categories = Repository(db, Category)
        self.products = Repository(db, Product)
        self.variants = Repository(db, ProductVariant)

    def list_products(
        self,
        limit: int,
        offset: int,
        franchise: str | None = None,
        active: bool | None = None,
    ) -> list[Product]:
        stmt = select(Product)
        if franchise:
            stmt = stmt.where(Product.franchise.ilike(f"%{franchise}%"))
        if active is not None:
            stmt = stmt.where(Product.active == active)
        return list(self.db.scalars(stmt.offset(offset).limit(limit)))

    def get_variant_by_sku(self, sku: str) -> ProductVariant | None:
        return self.db.scalar(select(ProductVariant).where(ProductVariant.sku == sku))
