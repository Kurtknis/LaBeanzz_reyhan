"""
Replace unavailable beans in an existing blend.

This builds a request and hands it to the normal generation pipeline, so the
result goes through the same candidate filtering, Pydantic validation, retry
and ai_generations logging as a fresh generation. Nothing is saved until the
owner saves the draft.
"""
from __future__ import annotations

from ..models import Blend
from ..schemas.ai import GenerateBlendRequest, SubstituteRequest
from . import blend_generation_service
from .errors import ServiceError

_AVAILABLE = ("AVAILABLE", "LOW_STOCK")


def _is_unavailable(item) -> bool:
    bean = item.bean
    return bean is None or bean.status not in _AVAILABLE or bean.stock_kg <= 0


def _build_prompt(blend: Blend, missing) -> str:
    recipe = ", ".join(f"{i.bean.name} {i.percentage}%" for i in blend.items if i.bean)
    gone = ", ".join(i.bean.name for i in missing if i.bean)
    lines = [
        f'Rework the existing blend "{blend.name}" because these beans are unavailable: {gone}.',
        f"Current recipe: {recipe}.",
    ]
    computed = (blend.predicted_profile or {}).get("computed")
    if computed:
        lines.append(
            "Keep the flavor target close to the original: "
            f"acidity {computed['acidity']}, body {computed['body']}, "
            f"sweetness {computed['sweetness']}."
        )
    lines.append(
        "Keep the remaining available beans where sensible and choose the closest "
        "replacement for each missing bean. Re-balance the percentages."
    )
    return " ".join(lines)[:1000]


def substitute_bean(owner_id, body: SubstituteRequest) -> dict:
    blend = Blend.query.filter_by(id=body.blend_id, owner_id=owner_id).first()
    if blend is None:
        raise ServiceError("Not found.", 404)

    if body.missing_bean_id is not None:
        missing = [i for i in blend.items if i.coffee_bean_id == body.missing_bean_id]
        if not missing:
            raise ServiceError("That bean is not part of this blend.", 422)
    else:
        missing = [i for i in blend.items if _is_unavailable(i)]
        if not missing:
            raise ServiceError("Every bean in this blend is still available.", 422)

    request = GenerateBlendRequest(
        prompt=_build_prompt(blend, missing),
        style=blend.style or "espresso",
    )
    return blend_generation_service.generate_blend(
        request,
        owner_id,
        exclude_bean_ids={str(i.coffee_bean_id) for i in missing},
        kind="SUBSTITUTE",
    )
