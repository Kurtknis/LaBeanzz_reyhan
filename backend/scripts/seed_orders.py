"""
seed_orders.py

Adds order history and on-hand stock for the demo owner so the Phase 7 demo
shows something immediately: a monthly spend chart and a "Reorder soon" card.

Run after scripts.seed and scripts.seed_feedback (it needs the demo owner and
their active "Morning Ritual" blend):

    python -m scripts.seed_orders

Idempotent: seeded orders carry a marker in `notes` and are skipped on re-run.
Order history is inserted directly as COMPLETED, so bean stock is untouched.
"""
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models import Blend, Order, OrderItem, OwnerStock, User
from app.services import business_rules as rules

app = create_app(os.getenv("FLASK_ENV", "development"))

OWNER_GOOGLE_SUB = "seed_owner_demo_01"
BLEND_NAME = "Morning Ritual"
MARKER = "seed-demo-history"
# kg ordered in each of the five months before this one, oldest first
HISTORY_KG = [22, 30, 26, 35, 28]
# kg on hand per recipe bean, in recipe order: the first runs out in 6 days at 2.5 kg/day
ON_HAND_KG = [9, 30, 40]


def seed_orders():
    with app.app_context():
        owner = User.query.filter_by(google_sub=OWNER_GOOGLE_SUB).first()
        if owner is None:
            print("  Demo owner not found. Run scripts.seed_feedback first.")
            return
        blend = Blend.query.filter_by(owner_id=owner.id, name=BLEND_NAME).first()
        if blend is None or not blend.items:
            print("  Demo blend not found. Run scripts.seed_feedback first.")
            return

        # On-hand stock: low enough that the reorder card fires
        for item, kg in zip(blend.items, ON_HAND_KG):
            row = OwnerStock.query.filter_by(owner_id=owner.id, coffee_bean_id=item.coffee_bean_id).first()
            if row is None:
                row = OwnerStock(owner_id=owner.id, coffee_bean_id=item.coffee_bean_id, quantity_kg=kg)
                db.session.add(row)
            else:
                row.quantity_kg = kg
        print(f"  Owner stock set for {min(len(blend.items), len(ON_HAND_KG))} beans.")

        # Order history for the spend chart
        if Order.query.filter_by(owner_id=owner.id, notes=MARKER).count():
            print("  Order history already seeded.")
        else:
            now = datetime.now(timezone.utc)
            past_months = rules.month_keys(now, 6)[:-1]            # everything before this month
            for key, total_kg in zip(past_months, HISTORY_KG):
                year, month = (int(p) for p in key.split("-"))
                placed_at = datetime(year, month, 10, 9, 0, tzinfo=timezone.utc)

                by_supplier: dict = {}
                for bean_id_pct in blend.items:
                    by_supplier.setdefault(bean_id_pct.bean.supplier_id, []).append(bean_id_pct)

                for supplier_id, items in by_supplier.items():
                    lines = [
                        (i.bean, (Decimal(total_kg) * i.percentage / 100).quantize(Decimal("0.01")))
                        for i in items
                    ]
                    order = Order(
                        owner_id=owner.id,
                        supplier_id=supplier_id,
                        status="COMPLETED",
                        total_price=sum((qty * bean.price_per_kg for bean, qty in lines), Decimal("0")),
                        currency=app.config["DEFAULT_CURRENCY"],
                        source_blend_id=blend.id,
                        notes=MARKER,
                        created_at=placed_at,
                        updated_at=placed_at,
                    )
                    db.session.add(order)
                    db.session.flush()
                    for bean, qty in lines:
                        db.session.add(OrderItem(
                            order_id=order.id, coffee_bean_id=bean.id,
                            quantity_kg=qty, unit_price=bean.price_per_kg,
                        ))
            print(f"  Seeded order history for {len(past_months)} months.")

        db.session.commit()
        print("Done.")


if __name__ == "__main__":
    seed_orders()
