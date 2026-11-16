from datetime import datetime, timezone
from typing import Optional

from ..extensions import db
from ..models import Preset
from ..schemas.blends import CreatePresetRequest, PatchPresetRequest


def list_presets(owner_id) -> list[Preset]:
    return Preset.query.filter_by(owner_id=owner_id).order_by(Preset.name).all()


def get_preset(preset_id, owner_id) -> Optional[Preset]:
    return Preset.query.filter_by(id=preset_id, owner_id=owner_id).first()


def create_preset(owner_id, body: CreatePresetRequest) -> tuple[Preset, None] | tuple[None, str]:
    existing = Preset.query.filter_by(owner_id=owner_id, name=body.name).first()
    if existing:
        return None, f"A preset named '{body.name}' already exists."

    preset = Preset(
        owner_id=owner_id,
        name=body.name,
        flavor_preferences=body.flavor_preferences,
        acidity_pref=body.acidity_pref,
        body_pref=body.body_pref,
        sweetness_pref=body.sweetness_pref,
        brewing_method=body.brewing_method,
        coffee_style=body.coffee_style,
        notes=body.notes,
    )
    db.session.add(preset)
    db.session.commit()
    return preset, None


def patch_preset(preset: Preset, body: PatchPresetRequest) -> tuple[Preset, None] | tuple[None, str]:
    if body.name is not None and body.name != preset.name:
        collision = Preset.query.filter_by(owner_id=preset.owner_id, name=body.name).first()
        if collision:
            return None, f"A preset named '{body.name}' already exists."
        preset.name = body.name

    for field in ("flavor_preferences", "acidity_pref", "body_pref",
                  "sweetness_pref", "brewing_method", "coffee_style", "notes"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(preset, field, val)

    preset.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return preset, None


def delete_preset(preset: Preset) -> None:
    db.session.delete(preset)
    db.session.commit()
