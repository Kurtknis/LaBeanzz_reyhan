"""add knowledge_chunks and ai_generations tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Vector dimension must match the embedding model (text-embedding-3-small = 1536)
VECTOR_DIM = 1536


def upgrade() -> None:
    # Enable pgvector extension (safe to run multiple times)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "knowledge_chunks",
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
            nullable=True,
        ),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        # vector column — type registered by pgvector
        sa.Column(
            "embedding",
            sa.Text,  # placeholder; replaced by raw DDL below
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Replace placeholder TEXT column with actual vector type
    op.execute(
        f"ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector({VECTOR_DIM}) USING NULL"
    )

    op.create_index("ix_knowledge_chunks_owner_id", "knowledge_chunks", ["owner_id"])
    op.create_index(
        "ix_knowledge_chunks_source",
        "knowledge_chunks",
        ["owner_id", "source_type"],
    )
    # HNSW index for cosine similarity search
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding "
        "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "ai_generations",
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
        sa.Column("kind", sa.String(30), nullable=False, server_default="GENERATE"),
        sa.Column("input", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "retrieved_chunk_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
        sa.Column("raw_output", sa.Text, nullable=True),
        sa.Column("validated_output", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(10), nullable=False, server_default="OK"),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('OK', 'INVALID', 'ERROR')", name="ck_ai_gen_status"
        ),
        sa.CheckConstraint(
            "kind IN ('GENERATE', 'SUBSTITUTE', 'CHAT', 'FEEDBACK_ANALYSIS')",
            name="ck_ai_gen_kind",
        ),
    )
    op.create_index("ix_ai_generations_owner_id", "ai_generations", ["owner_id"])


def downgrade() -> None:
    op.drop_table("ai_generations")
    op.drop_table("knowledge_chunks")
