"""add blends, blend_items, and presets tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BLEND_STATUSES = ("DRAFT", "ACTIVE", "ARCHIVED")
BLEND_STYLES = ("espresso", "filter", "milk")


def upgrade() -> None:
    op.create_table(
        "blends",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.String(10),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "source_generation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_generations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("predicted_profile", postgresql.JSONB, nullable=True),
        sa.Column("daily_usage_kg", sa.Numeric(8, 2), nullable=True),
        sa.Column("style", sa.String(10), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            f"status IN {BLEND_STATUSES}", name="ck_blend_status"
        ),
        sa.CheckConstraint(
            f"style IS NULL OR style IN {BLEND_STYLES}", name="ck_blend_style"
        ),
        sa.CheckConstraint("version >= 1", name="ck_blend_version"),
    )

    op.create_index("ix_blends_owner_id", "blends", ["owner_id"])
    op.create_index(
        "ix_blends_owner_status", "blends", ["owner_id", "status"]
    )

    op.create_table(
        "blend_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "blend_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("blends.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "coffee_bean_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("coffee_beans.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("percentage", sa.Integer, nullable=False),
        sa.UniqueConstraint("blend_id", "coffee_bean_id", name="uq_blend_item"),
        sa.CheckConstraint(
            "percentage >= 1 AND percentage <= 100", name="ck_blend_item_pct"
        ),
    )

    op.create_index("ix_blend_items_blend_id", "blend_items", ["blend_id"])

    op.create_table(
        "presets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "flavor_preferences",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column("acidity_pref", sa.Numeric(3, 1), nullable=True),
        sa.Column("body_pref", sa.Numeric(3, 1), nullable=True),
        sa.Column("sweetness_pref", sa.Numeric(3, 1), nullable=True),
        sa.Column("brewing_method", sa.String(50), nullable=True),
        sa.Column("coffee_style", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("owner_id", "name", name="uq_preset_name"),
        sa.CheckConstraint(
            "acidity_pref IS NULL OR (acidity_pref >= 0 AND acidity_pref <= 10)",
            name="ck_preset_acidity",
        ),
        sa.CheckConstraint(
            "body_pref IS NULL OR (body_pref >= 0 AND body_pref <= 10)",
            name="ck_preset_body",
        ),
        sa.CheckConstraint(
            "sweetness_pref IS NULL OR (sweetness_pref >= 0 AND sweetness_pref <= 10)",
            name="ck_preset_sweetness",
        ),
    )

    op.create_index("ix_presets_owner_id", "presets", ["owner_id"])


def downgrade() -> None:
    op.drop_table("presets")
    op.drop_table("blend_items")
    op.drop_table("blends")
