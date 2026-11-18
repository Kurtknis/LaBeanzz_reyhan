from flask import Blueprint, current_app, g, jsonify, request
from pydantic import ValidationError

from ..decorators import require_auth, require_role
from ..extensions import db
from ..responses import service_error, validation_error
from ..schemas.orders import OwnerStockRequest
from ..services import insights_service, stock_service
from ..services.errors import ServiceError

insights_bp = Blueprint("insights", __name__)


def _months() -> int:
    return max(1, min(request.args.get("months", 6, type=int), 24))


@insights_bp.get("/dashboard/summary")
@require_auth
@require_role("OWNER")
def dashboard_summary():
    return jsonify(insights_service.dashboard_summary(g.current_user.id)), 200


@insights_bp.get("/insights/spend")
@require_auth
@require_role("OWNER")
def spend():
    return jsonify(insights_service.spend_by_month(g.current_user.id, _months())), 200


@insights_bp.get("/insights/volume")
@require_auth
@require_role("OWNER")
def volume():
    return jsonify(insights_service.volume_by_month(g.current_user.id, _months())), 200


@insights_bp.get("/insights/reorder")
@require_auth
@require_role("OWNER")
def reorder():
    return jsonify({
        "threshold_days": current_app.config["REORDER_THRESHOLD_DAYS"],
        "items": insights_service.reorder_status(g.current_user.id),
    }), 200


@insights_bp.get("/owner-stock")
@require_auth
@require_role("OWNER")
def list_owner_stock():
    rows = stock_service.list_stock(g.current_user.id)
    return jsonify({"items": [r.to_dict() for r in rows]}), 200


@insights_bp.patch("/owner-stock")
@require_auth
@require_role("OWNER")
def set_owner_stock():
    try:
        body = OwnerStockRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error(exc)

    try:
        row = stock_service.set_stock(
            g.current_user.id, body.coffee_bean_id, body.quantity_kg
        )
    except ServiceError as exc:
        db.session.rollback()
        return service_error(exc)
    return jsonify(row.to_dict()), 200
