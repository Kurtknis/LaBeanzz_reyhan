"""
Blend and preset business logic.

All multi-step operations run inside a single db.session transaction so that
partial writes never reach the database.  Routes call these functions and
return the result; they do not touch db.session directly.
"""
from datetime import datetime, timezone
from typing import Optional
from decimal import Decimal

from ..extensions import db
from ..models import Blend, BlendItem, CoffeeBean, AIGeneration
from ..schemas.blends import (
    CreateBlendRequest,
    PatchBlendRequest,
    BlendStatusRequest,
)


# ─── Allowed status transitions ───────────────────────────────────────────────

TRANSITIONS: dict[str, set[str]] = {
    "DRAFT":    {"ACTIVE", "ARCHIVED"},
    "ACTIVE":   {"ARCHIVED"},
    "ARCHIVED": {"ACTIVE"},
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _compute_profile(items: list[BlendItem]) -> dict:
    """Weighted average acidity/body/sweetness from stored bean values."""
    acidity = body = sweetness = 0.0
    for item in items:
        pct = item.percentage / 100
        acidity   += float(item.bean.acidity)   * pct
        body      += float(item.bean.body)       * pct
        sweetness += float(item.bean.sweetness)  * pct
    return {
        "computed": {
            "acidity":   round(acidity, 2),
            "body":      round(body, 2),
            "sweetness": round(sweetness, 2),
        }
    }


def _resolve_beans(item_inputs, candidate_statuses=("AVAILABLE", "LOW_STOCK")):
    """
    Fetch beans by id.  Returns (bean_map, error_message).
    bean_map: {bean_id_str: CoffeeBean}
    """
    ids = [i.coffee_bean_id for i in item_inputs]
    beans = CoffeeBean.query.filter(CoffeeBean.id.in_(ids)).all()
    bean_map = {str(b.id): b for b in beans}

    missing = [bid for bid in ids if bid not in bean_map]
    if missing:
        return None, f"Beans not found: {missing}"

    unavailable = [
        bean_map[bid].name
        for bid in ids
        if bean_map[bid].status not in candidate_statuses
    ]
    if unavailable:
        return None, f"Beans not available: {unavailable}"

    return bean_map, None


# ─── Blend CRUD ───────────────────────────────────────────────────────────────

def create_blend(owner_id, body: CreateBlendRequest) -> tuple[Blend, None] | tuple[None, str]:
    """Create a new blend inside a single transaction. Returns (blend, error)."""
    bean_map, err = _resolve_beans(body.items)
    if err:
        return None, err

    # Validate source_generation_id belongs to this owner
    source_gen = None
    if body.source_generation_id:
        source_gen = AIGeneration.query.filter_by(
            id=body.source_generation_id, owner_id=owner_id
        ).first()
        if source_gen is None:
            return None, "Generation not found."

    blend = Blend(
        owner_id=owner_id,
        name=body.name,
        description=body.description,
        style=body.style,
        source_generation_id=body.source_generation_id if source_gen else None,
        status="DRAFT",
        version=1,
    )
    db.session.add(blend)
    db.session.flush()  # get blend.id

    items_objs = []
    for inp in body.items:
        bi = BlendItem(
            blend_id=blend.id,
            coffee_bean_id=inp.coffee_bean_id,
            percentage=inp.percentage,
        )
        db.session.add(bi)
        items_objs.append(bi)

    db.session.flush()
    # Eager-load beans for profile computation
    for bi in items_objs:
        bi.bean = bean_map[str(bi.coffee_bean_id)]

    blend.predicted_profile = _compute_profile(items_objs)
    db.session.commit()
    return blend, None


def get_blend(blend_id, owner_id) -> Optional[Blend]:
    """Return blend scoped to owner, or None (→ 404)."""
    return Blend.query.filter_by(id=blend_id, owner_id=owner_id).first()


def list_blends(owner_id, status_filter=None, page=1, per_page=20):
    q = Blend.query.filter_by(owner_id=owner_id)
    if status_filter:
        q = q.filter_by(status=status_filter)
    return q.order_by(Blend.updated_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


def patch_blend(blend: Blend, body: PatchBlendRequest) -> tuple[Blend, None] | tuple[None, str]:
    """Update name/description/style/items. Recipe edit bumps version."""
    if body.name is not None:
        blend.name = body.name
    if body.description is not None:
        blend.description = body.description
    if body.style is not None:
        blend.style = body.style

    if body.items is not None:
        bean_map, err = _resolve_beans(body.items)
        if err:
            return None, err

        # Remove old items
        BlendItem.query.filter_by(blend_id=blend.id).delete()
        db.session.flush()

        items_objs = []
        for inp in body.items:
            bi = BlendItem(
                blend_id=blend.id,
                coffee_bean_id=inp.coffee_bean_id,
                percentage=inp.percentage,
            )
            db.session.add(bi)
            items_objs.append(bi)

        db.session.flush()
        for bi in items_objs:
            bi.bean = bean_map[str(bi.coffee_bean_id)]

        blend.predicted_profile = _compute_profile(items_objs)
        blend.version = blend.version + 1

    blend.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return blend, None


def set_blend_status(blend: Blend, body: BlendStatusRequest) -> tuple[Blend, None] | tuple[None, str]:
    """Validate and apply a status transition."""
    allowed = TRANSITIONS.get(blend.status, set())
    if body.status not in allowed:
        return None, f"Cannot transition from {blend.status} to {body.status}."

    blend.status = body.status
    if body.status == "ACTIVE" and body.daily_usage_kg is not None:
        blend.daily_usage_kg = body.daily_usage_kg
    blend.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return blend, None


def duplicate_blend(blend: Blend, owner_id) -> Blend:
    """Create a DRAFT copy of an existing blend."""
    new_blend = Blend(
        owner_id=owner_id,
        name=f"{blend.name} (copy)",
        description=blend.description,
        style=blend.style,
        status="DRAFT",
        predicted_profile=blend.predicted_profile,
        version=1,
    )
    db.session.add(new_blend)
    db.session.flush()

    for item in blend.items:
        db.session.add(BlendItem(
            blend_id=new_blend.id,
            coffee_bean_id=item.coffee_bean_id,
            percentage=item.percentage,
        ))

    db.session.commit()
    return new_blend
