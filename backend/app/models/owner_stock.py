import uuid
from datetime import datetime, timezone
from ..extensions import db


class OwnerStock(db.Model):
    """Kilograms of a bean the owner currently holds. Feeds reorder intelligence."""

    __tablename__ = "owner_stock"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    coffee_bean_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("coffee_beans.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity_kg = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    bean = db.relationship("CoffeeBean")

    __table_args__ = (
        db.UniqueConstraint("owner_id", "coffee_bean_id", name="uq_owner_stock"),
    )

    def to_dict(self) -> dict:
        return {
            "coffee_bean_id": str(self.coffee_bean_id),
            "name": self.bean.name if self.bean else None,
            "origin": self.bean.origin if self.bean else None,
            "quantity_kg": float(self.quantity_kg),
            "updated_at": self.updated_at.isoformat(),
        }
