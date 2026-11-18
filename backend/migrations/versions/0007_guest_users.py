"""guest users

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-19

Guests have no Google identity, so google_sub becomes nullable. A CHECK keeps
that exception limited to guests: every real account still needs a google_sub.
The unique constraint on google_sub is untouched; Postgres allows many NULLs.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "google_sub", existing_type=sa.String(128), nullable=True)
    op.add_column(
        "users",
        sa.Column("is_guest", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("guest_ip_hash", sa.String(64), nullable=True))
    op.create_check_constraint(
        "ck_users_google_sub_or_guest", "users", "is_guest = true OR google_sub IS NOT NULL"
    )
    # Partial indexes: only guest rows are ever searched by these columns
    op.create_index(
        "ix_users_guest_ip_created", "users", ["guest_ip_hash", "created_at"],
        postgresql_where=sa.text("is_guest"),
    )
    op.create_index(
        "ix_users_guest_created", "users", ["created_at"],
        postgresql_where=sa.text("is_guest"),
    )


def downgrade() -> None:
    # google_sub can only go back to NOT NULL once the guests are gone.
    # Their data is deleted with them (all user-owned tables cascade).
    op.execute("DELETE FROM users WHERE is_guest")
    op.drop_index("ix_users_guest_created", table_name="users")
    op.drop_index("ix_users_guest_ip_created", table_name="users")
    op.drop_constraint("ck_users_google_sub_or_guest", "users", type_="check")
    op.drop_column("users", "guest_ip_hash")
    op.drop_column("users", "is_guest")
    op.alter_column("users", "google_sub", existing_type=sa.String(128), nullable=False)
