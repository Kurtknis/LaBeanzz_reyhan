"""add orders, order_items and owner_stock

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORDER_STATUSES = (
    "PENDING", "CONFIRMED", "PREPARING", "READY",
    "SHIPPED", "DELIVERED", "COMPLETED", "CANCELLED",
)


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def upgrade() -> None:
    op.create_table(
        "orders",
        _uuid_pk(),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="PENDING"),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("source_blend_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("blends.id", ondelete="SET NULL"), nullable=True),
        sa.Column("eta_date", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(f"status IN {ORDER_STATUSES}", name="ck_order_status"),
        sa.CheckConstraint("total_price >= 0", name="ck_order_total"),
    )
    op.create_index("ix_orders_owner_status", "orders", ["owner_id", "status"])
    op.create_index("ix_orders_supplier_status", "orders", ["supplier_id", "status"])
    op.create_index("ix_orders_group_id", "orders", ["group_id"])

    op.create_table(
        "order_items",
        _uuid_pk(),
        sa.Column("order_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("coffee_bean_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("coffee_beans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity_kg", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("quantity_kg > 0", name="ck_order_item_qty"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    op.create_table(
        "owner_stock",
        _uuid_pk(),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("coffee_bean_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("coffee_beans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity_kg", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("owner_id", "coffee_bean_id", name="uq_owner_stock"),
        sa.CheckConstraint("quantity_kg >= 0", name="ck_owner_stock_qty"),
    )


def downgrade() -> None:
    op.drop_table("owner_stock")
    op.drop_table("order_items")
    op.drop_table("orders")
