"""add feedback table

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BREW_CONTEXTS = ("espresso", "filter", "milk")


def upgrade() -> None:
    op.create_table(
        "feedback",
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
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("overall",   sa.Integer, nullable=False),
        sa.Column("flavor",    sa.Integer, nullable=False),
        sa.Column("body",      sa.Integer, nullable=False),
        sa.Column("acidity",   sa.Integer, nullable=False),
        sa.Column("sweetness", sa.Integer, nullable=False),
        sa.Column("brew_context", sa.String(10), nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("recipe_snapshot", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Rating range checks
        sa.CheckConstraint("overall   >= 1 AND overall   <= 5", name="ck_fb_overall"),
        sa.CheckConstraint("flavor    >= 1 AND flavor    <= 5", name="ck_fb_flavor"),
        sa.CheckConstraint("body      >= 1 AND body      <= 5", name="ck_fb_body"),
        sa.CheckConstraint("acidity   >= 1 AND acidity   <= 5", name="ck_fb_acidity"),
        sa.CheckConstraint("sweetness >= 1 AND sweetness <= 5", name="ck_fb_sweetness"),
        sa.CheckConstraint(
            f"brew_context IN {BREW_CONTEXTS}", name="ck_fb_brew_context"
        ),
    )

    op.create_index("ix_feedback_blend_id", "feedback", ["blend_id"])
    op.create_index("ix_feedback_owner_id", "feedback", ["owner_id"])
    op.create_index(
        "ix_feedback_owner_created",
        "feedback",
        ["owner_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("feedback")
