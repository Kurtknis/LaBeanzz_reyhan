"""
Pure business rules for orders and reorder intelligence.

Nothing here touches Flask or the database, so the rules can be tested
without any infrastructure.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# Order lifecycle ------------------------------------------------------------

SUPPLIER_FLOW = ("PENDING", "CONFIRMED", "PREPARING", "READY", "SHIPPED", "DELIVERED")
TERMINAL_STATUSES = ("COMPLETED", "CANCELLED")
ALL_ORDER_STATUSES = SUPPLIER_FLOW + TERMINAL_STATUSES
OWNER_CANCELLABLE = ("PENDING", "CONFIRMED")


def can_transition(role: str, current: str, target: str) -> bool:
    """
    Supplier: one step forward along SUPPLIER_FLOW, never skipping or going back.
    Owner: cancel while PENDING or CONFIRMED, mark COMPLETED after DELIVERED.
    """
    if role == "SUPPLIER":
        if current not in SUPPLIER_FLOW:
            return False
        idx = SUPPLIER_FLOW.index(current)
        return idx + 1 < len(SUPPLIER_FLOW) and SUPPLIER_FLOW[idx + 1] == target
    if role == "OWNER":
        if target == "CANCELLED":
            return current in OWNER_CANCELLABLE
        if target == "COMPLETED":
            return current == "DELIVERED"
    return False


# Reordering a blend ---------------------------------------------------------

_CENT = Decimal("0.01")


def split_by_percentage(
    recipe: list[tuple[str, int]], total_kg: Decimal
) -> list[tuple[str, Decimal]]:
    """Turn (bean_id, percentage) pairs into (bean_id, kg) for a total quantity."""
    return [
        (bean_id, (total_kg * pct / Decimal(100)).quantize(_CENT, rounding=ROUND_HALF_UP))
        for bean_id, pct in recipe
    ]


# Reorder intelligence -------------------------------------------------------

def days_remaining(
    recipe: list[tuple[str, str, int]],
    stock_kg: dict[str, Decimal | float],
    daily_usage_kg: Decimal | float,
) -> tuple[float, str] | None:
    """
    days_remaining = min over beans of stock / (daily_usage * pct / 100).

    recipe: (bean_id, bean_name, percentage) per component.
    Returns (days, bean_id_that_runs_out_first), or None when it cannot be
    computed (no usage figure or an empty recipe).
    """
    usage = float(daily_usage_kg or 0)
    if usage <= 0:
        return None

    worst: tuple[float, str] | None = None
    for bean_id, _name, pct in recipe:
        bean_usage = usage * pct / 100
        if bean_usage <= 0:
            continue
        days = float(stock_kg.get(bean_id, 0)) / bean_usage
        if worst is None or days < worst[0]:
            worst = (days, bean_id)
    return worst


# Calendar helpers -----------------------------------------------------------

def month_keys(now: datetime, n: int) -> list[str]:
    """The last n calendar months as 'YYYY-MM', oldest first, ending at now's month."""
    year, month = now.year, now.month
    keys: list[str] = []
    for _ in range(n):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(keys))


def month_key(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"
