from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError

from ..decorators import require_auth, require_role
from ..extensions import limiter
from ..models.ai_generation import AIGeneration
from ..schemas.ai import GenerateBlendRequest
from ..services import blend_generation_service

ai_bp = Blueprint("ai", __name__)

# 10 generation requests per minute per user (key = JWT sub via g.current_user)
_GENERATE_LIMIT = "10 per minute"


@ai_bp.post("/ai/generate-blend")
@require_auth
@require_role("OWNER")
@limiter.limit(_GENERATE_LIMIT, key_func=lambda: str(g.current_user.id))
def generate_blend():
    """
    POST /api/ai/generate-blend

    Body: { prompt, style?, preset_id?, max_price_per_kg? }
    Returns: { generation_id, draft: { blend_name, description, recipe, profile, reasoning, applied_feedback } }
    """
    try:
        body = GenerateBlendRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 422

    try:
        result = blend_generation_service.generate_blend(body, g.current_user.id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        return jsonify({"error": "Generation failed. Please try again."}), 503

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
