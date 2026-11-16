import uuid
from datetime import datetime, timezone
from ..extensions import db


class Blend(db.Model):
    __tablename__ = "blends"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    # DRAFT | ACTIVE | ARCHIVED
    status = db.Column(db.String(10), nullable=False, server_default="DRAFT")
    # FK to the generation that produced this blend (nullable — manual blends)
    source_generation_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("ai_generations.id", ondelete="SET NULL"),
        nullable=True,
    )
    predicted_profile = db.Column(db.JSON, nullable=True)
    # Set when status transitions to ACTIVE
    daily_usage_kg = db.Column(db.Numeric(8, 2), nullable=True)
    # espresso | filter | milk
    style = db.Column(db.String(10), nullable=True)
    version = db.Column(db.Integer, nullable=False, server_default="1")
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    items = db.relationship(
        "BlendItem", back_populates="blend", cascade="all, delete-orphan", lazy="select"
    )

    def to_dict(self, include_items: bool = True):
        d = {
            "id": str(self.id),
            "owner_id": str(self.owner_id),
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "source_generation_id": str(self.source_generation_id) if self.source_generation_id else None,
            "predicted_profile": self.predicted_profile,
            "daily_usage_kg": float(self.daily_usage_kg) if self.daily_usage_kg is not None else None,
            "style": self.style,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_items:
            d["items"] = [i.to_dict() for i in self.items]
        return d
