from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError

from ..decorators import require_auth, require_role
from ..extensions import db, limiter
from ..models.ai_generation import AIGeneration
from ..responses import service_error, validation_error
from ..schemas.ai import ChatRequest, GenerateBlendRequest, SubstituteRequest
from ..services import ai_lab_service, blend_generation_service, substitute_service
from ..services.errors import ServiceError

ai_bp = Blueprint("ai", __name__)

# One bucket of 10 requests per minute per user, shared by every /ai/* POST
_ai_limit = limiter.shared_limit(
    "10 per minute", scope="ai", key_func=lambda: str(g.current_user.id)
)


@ai_bp.post("/ai/generate-blend")
@require_auth
@require_role("OWNER")
@_ai_limit
def generate_blend():
    """
    POST /api/ai/generate-blend

    Body: { prompt, style?, preset_id?, max_price_per_kg? }
    Returns: { generation_id, draft: { blend_name, description, recipe, profile, reasoning, applied_feedback } }
    """
    try:
        body = GenerateBlendRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error(exc)

    try:
        result = blend_generation_service.generate_blend(body, g.current_user.id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception:
        return jsonify({"error": "Generation failed. Please try again."}), 503

    return jsonify(result), 200


@ai_bp.post("/ai/substitute")
@require_auth
@require_role("OWNER")
@_ai_limit
def substitute():
    """Propose a re-balanced recipe for a blend whose beans ran out. Saves nothing."""
    try:
        body = SubstituteRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error(exc)

    try:
        result = substitute_service.substitute_bean(g.current_user.id, body)
    except ServiceError as exc:
        db.session.rollback()
        return service_error(exc)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception:
        return jsonify({"error": "Substitution failed. Please try again."}), 503

    return jsonify(result), 200


@ai_bp.post("/ai/chat")
@require_auth
@require_role("OWNER")
@_ai_limit
def chat():
    """Free-form coffee chat grounded in the catalog and the owner's own feedback."""
    try:
        body = ChatRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error(exc)

    try:
        result = ai_lab_service.chat(g.current_user.id, body)
    except ServiceError as exc:
        db.session.rollback()
        return service_error(exc)
    return jsonify(result), 200


@ai_bp.post("/ai/analyze-feedback")
@require_auth
@require_role("OWNER")
@_ai_limit
def analyze_feedback():
    """Summarise the owner's feedback and refresh their rule-based taste constraints."""
    try:
        result = ai_lab_service.analyze_feedback(g.current_user.id)
    except ServiceError as exc:
        db.session.rollback()
        return service_error(exc)
    return jsonify(result), 200


@ai_bp.get("/ai/generations/<uuid:generation_id>")
@require_auth
@require_role("OWNER")
def get_generation(generation_id):
    """
    GET /api/ai/generations/:id

    Returns the logged generation record. Ownership enforced — another user's
    generation_id returns 404, not 403.
    """
    gen = AIGeneration.query.filter_by(
        id=generation_id,
        owner_id=g.current_user.id,
    ).first()

    if gen is None:
        return jsonify({"error": "Not found."}), 404

    return jsonify(gen.to_dict()), 200
