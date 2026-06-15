"""reserved stock and query indexes

Revision ID: 0002_reserved_stock
Revises: 0001_initial
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_reserved_stock"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_variants",
        sa.Column("reserved_quantity", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_products_franchise", "products", ["franchise"])
    op.create_index("ix_orders_status", "orders", ["status"])


def downgrade() -> None:
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_products_franchise", table_name="products")
    op.drop_column("product_variants", "reserved_quantity")
