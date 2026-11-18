from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError

from ..decorators import require_auth, require_role
from ..extensions import db
from ..responses import service_error, validation_error
from ..schemas.orders import CreateOrderRequest, OrderStatusRequest, ReorderBlendRequest
from ..services import business_rules as rules
from ..services import order_service
from ..services.errors import ServiceError

orders_bp = Blueprint("orders", __name__)


def _serialize(orders):
    for_supplier = g.current_user.role == "SUPPLIER"
    return [o.to_dict(for_supplier=for_supplier) for o in orders]


@orders_bp.get("/orders")
@require_auth
@require_role("OWNER", "SUPPLIER")
def list_orders():
    status = request.args.get("status")
    if status and status not in rules.ALL_ORDER_STATUSES:
        return jsonify({"error": "Unknown status filter."}), 422

    active_arg = request.args.get("active")
    active = None if active_arg is None else active_arg.lower() == "true"
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    pagination = order_service.list_orders(
        g.current_user, status=status, active=active, page=page, per_page=per_page
    )
    return jsonify({
        "items": _serialize(pagination.items),
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    }), 200


@orders_bp.post("/orders")
@require_auth
@require_role("OWNER")
def create_order():
    try:
        body = CreateOrderRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error(exc)

    try:
        orders = order_service.create_orders(
            g.current_user.id,
            [(i.coffee_bean_id, i.quantity_kg) for i in body.items],
            source_blend_id=body.source_blend_id,
            notes=body.notes,
        )
    except ServiceError as exc:
        db.session.rollback()
        return service_error(exc)

    reloaded = [order_service.get_order(g.current_user, o.id) for o in orders]
    return jsonify({"items": _serialize(reloaded)}), 201


@orders_bp.get("/orders/<uuid:order_id>")
@require_auth
@require_role("OWNER", "SUPPLIER")
def get_order(order_id):
    order = order_service.get_order(g.current_user, order_id)
    if order is None:
        return jsonify({"error": "Not found."}), 404
    return jsonify(_serialize([order])[0]), 200


@orders_bp.patch("/orders/<uuid:order_id>/status")
@require_auth
@require_role("OWNER", "SUPPLIER")
def update_order_status(order_id):
    try:
        body = OrderStatusRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error(exc)

    try:
        order = order_service.change_status(
            g.current_user, order_id, body.status, eta_date=body.eta_date
        )
    except ServiceError as exc:
        db.session.rollback()
        return service_error(exc)

    return jsonify(_serialize([order])[0]), 200


@orders_bp.post("/blends/<uuid:blend_id>/reorder")
@require_auth
@require_role("OWNER")
def reorder_blend(blend_id):
    try:
        body = ReorderBlendRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error(exc)

    try:
        orders = order_service.reorder_from_blend(
            g.current_user.id, blend_id, body.total_kg
        )
    except ServiceError as exc:
        db.session.rollback()
        return service_error(exc)

    reloaded = [order_service.get_order(g.current_user, o.id) for o in orders]
    return jsonify({"items": _serialize(reloaded)}), 201
