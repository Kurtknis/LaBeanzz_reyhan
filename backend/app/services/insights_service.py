"""Owner analytics: reorder intelligence, monthly spend/volume, dashboard summary."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from flask import current_app

from ..models import Blend, CoffeeBean, Order, OrderItem, OwnerStock
from . import business_rules as rules
from .visibility import visible_supplier_ids_for


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Reorder intelligence -------------------------------------------------------

def reorder_status(owner_id) -> list[dict]:
    """
    For every ACTIVE blend with a daily usage figure, how many days until the
    first bean runs out, and which bean that is. Soonest first.
    """
    threshold = current_app.config["REORDER_THRESHOLD_DAYS"]
    blends = (
        Blend.query
        .filter(Blend.owner_id == owner_id, Blend.status == "ACTIVE")
        .filter(Blend.daily_usage_kg.isnot(None))
        .all()
    )
    stock = {
        str(row.coffee_bean_id): row.quantity_kg
        for row in OwnerStock.query.filter_by(owner_id=owner_id).all()
    }

    results = []
    for blend in blends:
        recipe = [
            (str(i.coffee_bean_id), i.bean.name if i.bean else "Unknown", i.percentage)
            for i in blend.items
        ]
        worst = rules.days_remaining(recipe, stock, blend.daily_usage_kg)
        if worst is None:
            continue
        days, bean_id = worst
        bean_name = next(name for bid, name, _ in recipe if bid == bean_id)
        results.append({
            "blend_id": str(blend.id),
            "blend_name": blend.name,
            "daily_usage_kg": float(blend.daily_usage_kg),
            "days_remaining": round(days, 1),
            "limiting_bean": {"id": bean_id, "name": bean_name},
            "reorder_soon": days < threshold,
        })

    results.sort(key=lambda r: r["days_remaining"])
    return results


# Monthly spend and volume ---------------------------------------------------

def _monthly(owner_id, months: int):
    """(keys, spend_by_month, kg_by_month) over non-cancelled orders."""
    now = _now()
    keys = rules.month_keys(now, months)
    first_year, first_month = (int(p) for p in keys[0].split("-"))
    window_start = datetime(first_year, first_month, 1, tzinfo=timezone.utc)

    spend = {k: Decimal("0") for k in keys}
    kg = {k: Decimal("0") for k in keys}

    orders = (
        Order.query
        .filter(Order.owner_id == owner_id, Order.status != "CANCELLED")
        .filter(Order.created_at >= window_start)
        .all()
    )
    for order in orders:
        key = rules.month_key(order.created_at.astimezone(timezone.utc))
        if key not in spend:
            continue
        spend[key] += order.total_price
        kg[key] += sum((i.quantity_kg for i in order.items), Decimal("0"))
    return keys, spend, kg


def spend_by_month(owner_id, months: int = 6) -> dict:
    keys, spend, _ = _monthly(owner_id, months)
    return {
        "currency": current_app.config["DEFAULT_CURRENCY"],
        "items": [{"month": k, "amount": float(spend[k])} for k in keys],
    }


def volume_by_month(owner_id, months: int = 6) -> dict:
    keys, _, kg = _monthly(owner_id, months)
    return {"items": [{"month": k, "kg": float(kg[k])} for k in keys]}


# Producer spotlight ---------------------------------------------------------

def producer_spotlight(owner_id) -> dict | None:
    """
    A bean with a producer story, rotating daily. Built only from existing
    bean and supplier fields.
    """
    beans = (
        CoffeeBean.query
        .filter(CoffeeBean.producer_story.isnot(None), CoffeeBean.producer_story != "")
        .filter(CoffeeBean.status.in_(["AVAILABLE", "LOW_STOCK"]))
        .filter(CoffeeBean.supplier_id.in_(visible_supplier_ids_for(owner_id)))
        .order_by(CoffeeBean.id)
        .all()
    )
    if not beans:
        return None
    bean = beans[_now().date().toordinal() % len(beans)]
    return {
        "bean": {
            "id": str(bean.id),
            "name": bean.name,
            "origin": bean.origin,
            "region": bean.region,
            "producer": bean.producer,
            "farm": bean.farm,
            "producer_story": bean.producer_story,
        },
        "supplier": {
            "id": str(bean.supplier_id),
            "business_name": bean.supplier.company_name if bean.supplier else None,
        },
    }


# Dashboard ------------------------------------------------------------------

def dashboard_summary(owner_id) -> dict:
    keys, spend, kg = _monthly(owner_id, 1)
    this_month = keys[-1]

    active_orders = (
        Order.query
        .filter(Order.owner_id == owner_id)
        .filter(Order.status.notin_(rules.TERMINAL_STATUSES))
        .count()
    )
    active_blends = Blend.query.filter_by(owner_id=owner_id, status="ACTIVE").count()

    return {
        "active_orders": active_orders,
        "active_blends": active_blends,
        "month": this_month,
        "month_kg": float(kg[this_month]),
        "month_spend": float(spend[this_month]),
        "currency": current_app.config["DEFAULT_CURRENCY"],
        "reorder": [r for r in reorder_status(owner_id) if r["reorder_soon"]][:3],
        "spotlight": producer_spotlight(owner_id),
    }
