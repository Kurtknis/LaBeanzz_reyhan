"""
seed_feedback.py

Creates a demo owner account with an active blend and pre-existing feedback
so the Phase 5 demo path works immediately without any manual data entry.

The seeded blend has three "milk" feedback rows with low acidity ratings,
which will cause taste_adjustments to add an acidity_max constraint for the
"milk" brew context — proving the feedback loop is working.

Usage (from backend/):
    python -m scripts.seed_feedback

Idempotent: re-running is safe. The owner account and blend are keyed by a
stable google_sub so duplicates are skipped.
"""

import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models import User, OwnerProfile, CoffeeBean, Blend, BlendItem, Feedback
from app.services.feedback_service import _recompute_taste_adjustments

app = create_app(os.getenv("FLASK_ENV", "development"))

OWNER_GOOGLE_SUB = "seed_owner_demo_01"
OWNER_EMAIL      = "demo-owner@labeans.dev"
OWNER_NAME       = "Demo Owner"
BLEND_NAME       = "Morning Ritual"


def seed_feedback():
    with app.app_context():
        # ── 1. Demo owner ─────────────────────────────────────────────────────
        owner = User.query.filter_by(google_sub=OWNER_GOOGLE_SUB).first()
        if owner is None:
            owner = User(
                id=uuid.uuid4(),
                google_sub=OWNER_GOOGLE_SUB,
                email=OWNER_EMAIL,
                name=OWNER_NAME,
                role="OWNER",
            )
            db.session.add(owner)
            db.session.flush()

        profile = OwnerProfile.query.filter_by(user_id=owner.id).first()
        if profile is None:
            profile = OwnerProfile(
                user_id=owner.id,
                business_name="Demo Coffee",
                taste_adjustments={},
            )
            db.session.add(profile)
            db.session.flush()

        db.session.commit()
        print(f"  Owner: {owner.email}")

        # ── 2. Pick beans for the blend (first 3 available beans) ─────────────
        beans = (
            CoffeeBean.query
            .filter(CoffeeBean.status.in_(["AVAILABLE", "LOW_STOCK"]))
            .limit(3)
            .all()
        )
        if len(beans) < 2:
            print("  Not enough beans in catalog — run scripts.seed first.")
            return

        # ── 3. Demo blend (ACTIVE) ────────────────────────────────────────────
        blend = Blend.query.filter_by(owner_id=owner.id, name=BLEND_NAME).first()
        if blend is None:
            # Build a recipe: first bean 60%, second 30%, third 10% (or 70/30)
            if len(beans) == 2:
                recipe = [(beans[0], 70), (beans[1], 30)]
            else:
                recipe = [(beans[0], 60), (beans[1], 30), (beans[2], 10)]

            # Compute weighted profile
            acidity = body = sweetness = 0.0
            for b, pct in recipe:
                acidity   += float(b.acidity)   * (pct / 100)
                body      += float(b.body)       * (pct / 100)
                sweetness += float(b.sweetness)  * (pct / 100)

            blend = Blend(
                owner_id=owner.id,
                name=BLEND_NAME,
                description=(
                    "A smooth, full-bodied milk blend — the workhorse of the morning "
                    "rush. This recipe was seeded to demonstrate the feedback loop."
                ),
                style="milk",
                status="ACTIVE",
                daily_usage_kg=2.5,
                predicted_profile={
                    "computed": {
                        "acidity":   round(acidity, 2),
                        "body":      round(body, 2),
                        "sweetness": round(sweetness, 2),
                    }
                },
                version=1,
            )
            db.session.add(blend)
            db.session.flush()

            for b, pct in recipe:
                db.session.add(BlendItem(
                    blend_id=blend.id,
                    coffee_bean_id=b.id,
                    percentage=pct,
                ))

            db.session.commit()
            print(f"  Created blend: {blend.name}")
        else:
            print(f"  Blend already exists: {blend.name}")

        # ── 4. Pre-existing feedback (3 milk entries, all with low acidity) ───
        existing = Feedback.query.filter_by(blend_id=blend.id, owner_id=owner.id).count()
        if existing >= 3:
            print(f"  Feedback already seeded ({existing} rows).")
        else:
            feedback_data = [
                {
                    "overall": 4,
                    "flavor": 4,
                    "body": 5,
                    "acidity": 2,
                    "sweetness": 4,
                    "brew_context": "milk",
                    "comment": (
                        "Great body and sweetness for milk drinks, but the acidity "
                        "cuts through too much — feels sharp in a flat white."
                    ),
                },
                {
                    "overall": 3,
                    "flavor": 3,
                    "body": 4,
                    "acidity": 2,
                    "sweetness": 3,
                    "brew_context": "milk",
                    "comment": (
                        "Still too acidic for lattes. The body is good but the "
                        "brightness overwhelms the milk at our standard ratio."
                    ),
                },
                {
                    "overall": 4,
                    "flavor": 4,
                    "body": 5,
                    "acidity": 1,
                    "sweetness": 4,
                    "brew_context": "milk",
                    "comment": (
                        "Customers are noticing the acidity. Would prefer something "
                        "lower — maybe more Brazilian or Indonesian base beans."
                    ),
                },
            ]

            recipe_snapshot = [
                {"coffee_bean_id": str(item.coffee_bean_id), "percentage": item.percentage}
                for item in blend.items
            ]

            for fd in feedback_data:
                fb = Feedback(
                    blend_id=blend.id,
                    owner_id=owner.id,
                    recipe_snapshot=recipe_snapshot,
                    **fd,
                )
                db.session.add(fb)

            db.session.commit()
            print(f"  Seeded 3 feedback rows (low acidity for milk).")

        # ── 5. Recompute taste_adjustments ────────────────────────────────────
        _recompute_taste_adjustments(owner.id)
        db.session.commit()

        profile = OwnerProfile.query.filter_by(user_id=owner.id).first()
        print(f"  taste_adjustments: {profile.taste_adjustments}")
        print("Done.")


if __name__ == "__main__":
    seed_feedback()
