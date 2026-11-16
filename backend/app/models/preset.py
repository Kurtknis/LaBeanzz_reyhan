import uuid
from datetime import datetime, timezone
from ..extensions import db


class Preset(db.Model):
    __tablename__ = "presets"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(100), nullable=False)
    # Freeform JSON: { chocolate, caramel, fruitiness, ... }
    flavor_preferences = db.Column(db.JSON, nullable=False, server_default="{}")
    # 0.0 – 10.0 targets
    acidity_pref = db.Column(db.Numeric(3, 1), nullable=True)
    body_pref = db.Column(db.Numeric(3, 1), nullable=True)
    sweetness_pref = db.Column(db.Numeric(3, 1), nullable=True)
    brewing_method = db.Column(db.String(50), nullable=True)
    coffee_style = db.Column(db.String(10), nullable=True)
    notes = db.Column(db.Text, nullable=True)
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

    __table_args__ = (
        db.UniqueConstraint("owner_id", "name", name="uq_preset_name"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "owner_id": str(self.owner_id),
            "name": self.name,
            "flavor_preferences": self.flavor_preferences,
            "acidity_pref": float(self.acidity_pref) if self.acidity_pref is not None else None,
            "body_pref": float(self.body_pref) if self.body_pref is not None else None,
            "sweetness_pref": float(self.sweetness_pref) if self.sweetness_pref is not None else None,
            "brewing_method": self.brewing_method,
            "coffee_style": self.coffee_style,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
