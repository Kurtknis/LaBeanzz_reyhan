"""
Order creation, listing and lifecycle.

Every stock-changing path runs in one transaction and takes row locks on the
affected beans (ordered by id, so two requests cannot deadlock). Stock is
reserved when an order is created and released when it is cancelled.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from flask import current_app
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import Blend, CoffeeBean, Order, OrderItem
from . import business_rules as rules
from . import stock_service
from .errors import ServiceError

ORDERABLE_BEAN_STATUSES = ("AVAILABLE", "LOW_STOCK")


def _kg(value: Decimal) -> str:
    return format(Decimal(value).quantize(Decimal("0.01")), "f")


def _lock_beans(bean_ids) -> dict:
    beans = (
        CoffeeBean.query
        .filter(CoffeeBean.id.in_(list(bean_ids)))
        .order_by(CoffeeBean.id)
        .with_for_update()
        .all()
    )
    return {b.id: b for b in beans}


def _low_stock_kg() -> Decimal:
    return Decimal(str(current_app.config["LOW_STOCK_KG"]))


def _after_reserve(bean: CoffeeBean, low_kg: Decimal) -> None:
    if bean.stock_kg <= 0:
        bean.status = "OUT_OF_STOCK"
    elif bean.status == "AVAILABLE" and bean.stock_kg < low_kg:
        bean.status = "LOW_STOCK"


def _after_release(bean: CoffeeBean, was_empty: bool, low_kg: Decimal) -> None:
    # Only undo an OUT_OF_STOCK that the reservation itself caused
    if was_empty and bean.status == "OUT_OF_STOCK" and bean.stock_kg > 0:
        bean.status = "LOW_STOCK" if bean.stock_kg < low_kg else "AVAILABLE"
    elif bean.status == "LOW_STOCK" and bean.stock_kg >= low_kg:
        bean.status = "AVAILABLE"


# Create ---------------------------------------------------------------------

def create_orders(
    owner_id,
    lines: list[tuple[uuid.UUID, Decimal]],
    source_blend_id: uuid.UUID | None = None,
    notes: str | None = None,
) -> list[Order]:
    """
    Create one order per supplier from (bean_id, quantity_kg) lines.

    Unit prices are snapshotted from the bean and the total is computed here;
    nothing price-related is accepted from the client.
    """
    if source_blend_id is not None:
        if Blend.query.filter_by(id=source_blend_id, owner_id=owner_id).first() is None:
            raise ServiceError("Blend not found.", 404)

    beans = _lock_beans(bean_id for bean_id, _ in lines)
    low_kg = _low_stock_kg()

    by_supplier: dict = defaultdict(list)
    for bean_id, qty in lines:
        bean = beans.get(bean_id)
        if bean is None:
            raise ServiceError("One or more beans were not found.", 404)
        if bean.status not in ORDERABLE_BEAN_STATUSES:
            raise ServiceError(f"{bean.name} is not available to order.", 409)
        if qty > bean.stock_kg:
            raise ServiceError(
                f"Only {_kg(bean.stock_kg)} kg of {bean.name} is in stock, "
                f"but {_kg(qty)} kg was requested.",
                409,
            )
        by_supplier[bean.supplier_id].append((bean, qty))

    group_id = uuid.uuid4() if len(by_supplier) > 1 else None
    currency = current_app.config["DEFAULT_CURRENCY"]
    orders: list[Order] = []

    for supplier_id, supplier_lines in by_supplier.items():
        total = sum((qty * bean.price_per_kg for bean, qty in supplier_lines), Decimal("0"))
        order = Order(
            owner_id=owner_id,
            supplier_id=supplier_id,
            status="PENDING",
            total_price=total.quantize(Decimal("0.01")),
            currency=currency,
            source_blend_id=source_blend_id,
            group_id=group_id,
            notes=notes,
        )
        db.session.add(order)
        db.session.flush()
        for bean, qty in supplier_lines:
            db.session.add(OrderItem(
                order_id=order.id,
                coffee_bean_id=bean.id,
                quantity_kg=qty,
                unit_price=bean.price_per_kg,
            ))
            bean.stock_kg = bean.stock_kg - qty
            _after_reserve(bean, low_kg)
        orders.append(order)

    db.session.commit()
    return orders


def reorder_from_blend(owner_id, blend_id, total_kg: Decimal) -> list[Order]:
    """Order enough of every bean in a blend to make total_kg of it."""
    blend = Blend.query.filter_by(id=blend_id, owner_id=owner_id).first()
    if blend is None:
        raise ServiceError("Not found.", 404)
    if not blend.items:
        raise ServiceError("This blend has no recipe to order.", 422)

    parts = rules.split_by_percentage(
        [(str(i.coffee_bean_id), i.percentage) for i in blend.items], total_kg
    )
    lines = [(uuid.UUID(bean_id), qty) for bean_id, qty in parts if qty > 0]
    if not lines:
        raise ServiceError("That quantity is too small to split across the recipe.", 422)
    return create_orders(owner_id, lines, source_blend_id=blend.id)


# Read -----------------------------------------------------------------------

def _scope(user):
    """Orders visible to this user. Anything outside it simply does not exist."""
    if user.role == "OWNER":
        return Order.query.filter(Order.owner_id == user.id)
    supplier = user.supplier_profile
    if supplier is None:
        return Order.query.filter(sa.false())
    return Order.query.filter(Order.supplier_id == supplier.id)


def _eager(query):
    return query.options(
        selectinload(Order.items).selectinload(OrderItem.bean),
        selectinload(Order.supplier),
        selectinload(Order.owner),
    )


def list_orders(user, status=None, active=None, page=1, per_page=20):
    query = _eager(_scope(user))
    if status:
        query = query.filter(Order.status == status)
    if active is True:
        query = query.filter(Order.status.notin_(rules.TERMINAL_STATUSES))
    elif active is False:
        query = query.filter(Order.status.in_(rules.TERMINAL_STATUSES))
    return query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


def get_order(user, order_id):
    return _eager(_scope(user)).filter(Order.id == order_id).first()


# Lifecycle ------------------------------------------------------------------

def _release_stock(order: Order) -> None:
    beans = _lock_beans(item.coffee_bean_id for item in order.items)
    low_kg = _low_stock_kg()
    for item in order.items:
        bean = beans[item.coffee_bean_id]
        was_empty = bean.stock_kg <= 0
        bean.stock_kg = bean.stock_kg + item.quantity_kg
        _after_release(bean, was_empty, low_kg)


def change_status(user, order_id, target: str, eta_date: date | None = None) -> Order:
    # Lock the order row so two simultaneous transitions cannot both succeed
    order = _scope(user).filter(Order.id == order_id).with_for_update().first()
    if order is None:
        raise ServiceError("Not found.", 404)

    if not rules.can_transition(user.role, order.status, target):
        raise ServiceError(
            f"An order that is {order.status} cannot move to {target}.", 409
        )

    if target == "CANCELLED":
        _release_stock(order)
    elif target == "DELIVERED":
        for item in order.items:
            stock_service.add_stock(order.owner_id, item.coffee_bean_id, item.quantity_kg)

    order.status = target
    if eta_date is not None and user.role == "SUPPLIER":
        order.eta_date = eta_date

    db.session.commit()
    return get_order(user, order_id)
