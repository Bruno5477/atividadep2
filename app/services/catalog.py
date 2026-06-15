from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.models.catalog import Category, Product, ProductVariant, StockMovement
from app.repositories.catalog import CatalogRepository
from app.schemas.catalog import CategoryCreate, ProductCreate, StockAdjust, VariantCreate


class CatalogService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CatalogRepository(db)

    def create_category(self, data: CategoryCreate) -> Category:
        category = Category(**data.model_dump())
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def create_product(self, data: ProductCreate) -> Product:
        if not self.repo.categories.get(data.category_id):
            raise DomainError("CATEGORY_NOT_FOUND", "Categoria informada nao existe.", 404)
        product = Product(**data.model_dump())
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def create_variant(self, data: VariantCreate) -> ProductVariant:
        product = self.repo.products.get(data.product_id)
        if not product or not product.active:
            raise DomainError("PRODUCT_NOT_AVAILABLE", "Produto inexistente ou inativo.", 404)
        if self.repo.get_variant_by_sku(data.sku):
            raise DomainError("SKU_ALREADY_EXISTS", "SKU ja cadastrado.", 409, {"sku": data.sku})
        variant = ProductVariant(**data.model_dump())
        self.db.add(variant)
        self.db.flush()
        self.db.add(
            StockMovement(
                variant_id=variant.id,
                quantity_delta=data.stock_quantity,
                reason="initial_stock",
            )
        )
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def adjust_stock(self, variant_id: int, data: StockAdjust) -> ProductVariant:
        variant = self.repo.variants.get(variant_id)
        if not variant:
            raise DomainError("VARIANT_NOT_FOUND", "Variante nao encontrada.", 404)
        new_stock = variant.stock_quantity + data.quantity_delta
        if new_stock < variant.reserved_quantity:
            raise DomainError(
                "STOCK_BELOW_RESERVED",
                "Estoque fisico nao pode ficar menor que a quantidade reservada.",
                409,
                {"reserved_quantity": variant.reserved_quantity, "requested_stock": new_stock},
            )
        variant.stock_quantity = new_stock
        self.db.add(StockMovement(variant_id=variant.id, quantity_delta=data.quantity_delta, reason=data.reason))
        self.db.commit()
        self.db.refresh(variant)
        return variant
