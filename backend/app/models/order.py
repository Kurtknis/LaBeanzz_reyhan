import uuid
from datetime import datetime, timezone
from ..extensions import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    supplier_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Shared by the orders created from one multi-supplier request
    group_id = db.Column(db.UUID(as_uuid=True), nullable=True)
    # PENDING | CONFIRMED | PREPARING | READY | SHIPPED | DELIVERED | COMPLETED | CANCELLED
    status = db.Column(db.String(12), nullable=False, server_default="PENDING")
    total_price = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, server_default="USD")
    source_blend_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("blends.id", ondelete="SET NULL"),
        nullable=True,
    )
    eta_date = db.Column(db.Date, nullable=True)
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

    items = db.relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    supplier = db.relationship("Supplier")
    owner = db.relationship("User")

    def to_dict(self, for_supplier: bool = False) -> dict:
        d = {
            "id": str(self.id),
            "status": self.status,
            "total_price": float(self.total_price),
            "currency": self.currency,
            "eta_date": self.eta_date.isoformat() if self.eta_date else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "supplier": {
                "id": str(self.supplier_id),
                "business_name": self.supplier.company_name if self.supplier else None,
            },
            "items": [i.to_dict() for i in self.items],
        }
        if for_supplier:
            # Suppliers see who to ship to, never the owner's blends or analytics
            owner = self.owner
            profile = owner.owner_profile if owner else None
            d["owner"] = {
                "business_name": (profile.business_name if profile and profile.business_name else (owner.name if owner else None))
            }
        else:
            d["source_blend_id"] = str(self.source_blend_id) if self.source_blend_id else None
            d["group_id"] = str(self.group_id) if self.group_id else None
        return d


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    coffee_bean_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("coffee_beans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity_kg = db.Column(db.Numeric(10, 2), nullable=False)
    # Price per kg at the moment the order was placed
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)

    order = db.relationship("Order", back_populates="items")
    bean = db.relationship("CoffeeBean")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "coffee_bean_id": str(self.coffee_bean_id),
            "name": self.bean.name if self.bean else None,
            "origin": self.bean.origin if self.bean else None,
            "quantity_kg": float(self.quantity_kg),
            "unit_price": float(self.unit_price),
            "line_total": float(self.quantity_kg * self.unit_price),
        }
