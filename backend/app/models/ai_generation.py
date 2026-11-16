import uuid
from datetime import datetime, timezone
from ..extensions import db
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import String


class AIGeneration(db.Model):
    __tablename__ = "ai_generations"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # GENERATE | SUBSTITUTE | CHAT | FEEDBACK_ANALYSIS
    kind = db.Column(db.String(30), nullable=False, default="GENERATE")
    input = db.Column(db.JSON, nullable=False)
    retrieved_chunk_ids = db.Column(ARRAY(db.UUID(as_uuid=True)), nullable=True)
    raw_output = db.Column(db.Text, nullable=True)
    validated_output = db.Column(db.JSON, nullable=True)
    # OK | INVALID | ERROR
    status = db.Column(db.String(10), nullable=False, default="OK")
    model = db.Column(db.String(100), nullable=True)
    latency_ms = db.Column(db.Integer, nullable=True)
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "owner_id": str(self.owner_id),
            "kind": self.kind,
            "input": self.input,
            "validated_output": self.validated_output,
            "status": self.status,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }
