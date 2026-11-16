import uuid
from datetime import datetime, timezone
from ..extensions import db


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blend_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("blends.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 1–5 ratings
    overall   = db.Column(db.Integer, nullable=False)
    flavor    = db.Column(db.Integer, nullable=False)
    body      = db.Column(db.Integer, nullable=False)
    acidity   = db.Column(db.Integer, nullable=False)
    sweetness = db.Column(db.Integer, nullable=False)
    # espresso | filter | milk
    brew_context = db.Column(db.String(10), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    # Snapshot of the recipe at the time of feedback
    recipe_snapshot = db.Column(db.JSON, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "blend_id": str(self.blend_id),
            "owner_id": str(self.owner_id),
            "overall":   self.overall,
            "flavor":    self.flavor,
            "body":      self.body,
            "acidity":   self.acidity,
            "sweetness": self.sweetness,
            "brew_context": self.brew_context,
            "comment": self.comment,
            "recipe_snapshot": self.recipe_snapshot,
            "created_at": self.created_at.isoformat(),
        }
