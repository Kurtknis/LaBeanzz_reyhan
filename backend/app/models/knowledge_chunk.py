import uuid
from datetime import datetime, timezone
from ..extensions import db
from pgvector.sqlalchemy import Vector


class KnowledgeChunk(db.Model):
    __tablename__ = "knowledge_chunks"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # NULL = global knowledge; set = owner-private (feedback, blends)
    owner_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # DOC | BEAN | FEEDBACK | BLEND
    source_type = db.Column(db.String(20), nullable=False)
    source_id = db.Column(db.UUID(as_uuid=True), nullable=True)
    content = db.Column(db.Text, nullable=False)
    metadata_ = db.Column("metadata", db.JSON, nullable=False, default=dict)
    # Dimension set to 1536 (text-embedding-3-small). Must match embed model.
    embedding = db.Column(Vector(1536), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "owner_id": str(self.owner_id) if self.owner_id else None,
            "source_type": self.source_type,
            "source_id": str(self.source_id) if self.source_id else None,
            "content": self.content,
            "metadata": self.metadata_,
        }
