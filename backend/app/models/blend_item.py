import uuid
from ..extensions import db


class BlendItem(db.Model):
    __tablename__ = "blend_items"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blend_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("blends.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coffee_bean_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("coffee_beans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # integer 1–100; service layer enforces sum == 100
    percentage = db.Column(db.Integer, nullable=False)

    blend = db.relationship("Blend", back_populates="items")
    bean = db.relationship("CoffeeBean")

    __table_args__ = (
        db.UniqueConstraint("blend_id", "coffee_bean_id", name="uq_blend_item"),
    )

    def to_dict(self):
        bean_summary = None
        if self.bean:
            bean_summary = {
                "id": str(self.bean.id),
                "name": self.bean.name,
                "origin": self.bean.origin,
                "roast_level": self.bean.roast_level,
                "acidity": float(self.bean.acidity),
                "body": float(self.bean.body),
                "sweetness": float(self.bean.sweetness),
                "price_per_kg": float(self.bean.price_per_kg),
                "status": self.bean.status,
            }
        return {
            "id": str(self.id),
            "blend_id": str(self.blend_id),
            "coffee_bean_id": str(self.coffee_bean_id),
            "percentage": self.percentage,
            "bean": bean_summary,
        }
