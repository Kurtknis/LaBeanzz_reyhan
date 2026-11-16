from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError

from ..decorators import require_auth, require_role
from ..schemas.blends import (
    CreateBlendRequest,
    PatchBlendRequest,
    BlendStatusRequest,
    CreatePresetRequest,
    PatchPresetRequest,
)
from ..schemas.feedback import CreateFeedbackRequest
from ..services import blend_service, preset_service, feedback_service

blends_bp = Blueprint("blends", __name__)


# ─── Blends ───────────────────────────────────────────────────────────────────

@blends_bp.get("/blends")
@require_auth
@require_role("OWNER")
def list_blends():
    status_filter = request.args.get("status")
    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    pagination = blend_service.list_blends(
        owner_id=g.current_user.id,
        status_filter=status_filter,
        page=page,
        per_page=per_page,
    )
    return jsonify({
        "items": [b.to_dict(include_items=True) for b in pagination.items],
        "total": pagination.total,
        "page":  pagination.page,
        "pages": pagination.pages,
    }), 200


@blends_bp.post("/blends")
@require_auth
@require_role("OWNER")
def create_blend():
    try:
        body = CreateBlendRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 422

    blend, err = blend_service.create_blend(g.current_user.id, body)
    if err:
        return jsonify({"error": err}), 422

    return jsonify(blend.to_dict()), 201


@blends_bp.get("/blends/<uuid:blend_id>")
@require_auth
@require_role("OWNER")
def get_blend(blend_id):
    blend = blend_service.get_blend(blend_id, g.current_user.id)
    if blend is None:
        return jsonify({"error": "Not found."}), 404
    return jsonify(blend.to_dict()), 200


@blends_bp.patch("/blends/<uuid:blend_id>")
@require_auth
@require_role("OWNER")
def patch_blend(blend_id):
    blend = blend_service.get_blend(blend_id, g.current_user.id)
    if blend is None:
        return jsonify({"error": "Not found."}), 404

    try:
        body = PatchBlendRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 422

    blend, err = blend_service.patch_blend(blend, body)
    if err:
        return jsonify({"error": err}), 422

    return jsonify(blend.to_dict()), 200


@blends_bp.post("/blends/<uuid:blend_id>/status")
@require_auth
@require_role("OWNER")
def set_blend_status(blend_id):
    blend = blend_service.get_blend(blend_id, g.current_user.id)
    if blend is None:
        return jsonify({"error": "Not found."}), 404

    try:
        body = BlendStatusRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 422

    blend, err = blend_service.set_blend_status(blend, body)
    if err:
        return jsonify({"error": err}), 409

    return jsonify(blend.to_dict(include_items=False)), 200


@blends_bp.post("/blends/<uuid:blend_id>/duplicate")
@require_auth
@require_role("OWNER")
def duplicate_blend(blend_id):
    blend = blend_service.get_blend(blend_id, g.current_user.id)
    if blend is None:
        return jsonify({"error": "Not found."}), 404

    new_blend = blend_service.duplicate_blend(blend, g.current_user.id)
    return jsonify(new_blend.to_dict()), 201


# ─── Presets ──────────────────────────────────────────────────────────────────

@blends_bp.get("/presets")
@require_auth
@require_role("OWNER")
def list_presets():
    presets = preset_service.list_presets(g.current_user.id)
    return jsonify({"items": [p.to_dict() for p in presets]}), 200


@blends_bp.post("/presets")
@require_auth
@require_role("OWNER")
def create_preset():
    try:
        body = CreatePresetRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 422

    preset, err = preset_service.create_preset(g.current_user.id, body)
    if err:
        return jsonify({"error": err}), 409

    return jsonify(preset.to_dict()), 201


@blends_bp.patch("/presets/<uuid:preset_id>")
@require_auth
@require_role("OWNER")
def patch_preset(preset_id):
    preset = preset_service.get_preset(preset_id, g.current_user.id)
    if preset is None:
        return jsonify({"error": "Not found."}), 404

    try:
        body = PatchPresetRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 422

    preset, err = preset_service.patch_preset(preset, body)
    if err:
        return jsonify({"error": err}), 409

    return jsonify(preset.to_dict()), 200


@blends_bp.delete("/presets/<uuid:preset_id>")
@require_auth
@require_role("OWNER")
def delete_preset(preset_id):
    preset = preset_service.get_preset(preset_id, g.current_user.id)
    if preset is None:
        return jsonify({"error": "Not found."}), 404

    preset_service.delete_preset(preset)
    return "", 204


# ─── Feedback ─────────────────────────────────────────────────────────────────

@blends_bp.post("/blends/<uuid:blend_id>/feedback")
@require_auth
@require_role("OWNER")
def submit_feedback(blend_id):
    """Submit a feedback rating for one of the owner's blends."""
    blend = blend_service.get_blend(blend_id, g.current_user.id)
    if blend is None:
        return jsonify({"error": "Not found."}), 404

    try:
        body = CreateFeedbackRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 422

    fb = feedback_service.submit_feedback(blend, g.current_user.id, body)
    return jsonify(fb.to_dict()), 201


@blends_bp.get("/blends/<uuid:blend_id>/feedback")
@require_auth
@require_role("OWNER")
def list_feedback(blend_id):
    """Return all feedback for the blend (owner-scoped)."""
    # Confirm ownership — 404 if not theirs
    blend = blend_service.get_blend(blend_id, g.current_user.id)
    if blend is None:
        return jsonify({"error": "Not found."}), 404

    items = feedback_service.list_feedback(blend_id, g.current_user.id)
    return jsonify({"items": [f.to_dict() for f in items]}), 200
