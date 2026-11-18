"""Owner-side inventory: how many kg of each bean the owner holds."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..extensions import db
from ..models import CoffeeBean, OwnerStock
from .errors import ServiceError


def list_stock(owner_id) -> list[OwnerStock]:
    return (
        OwnerStock.query
        .filter_by(owner_id=owner_id)
        .join(CoffeeBean, CoffeeBean.id == OwnerStock.coffee_bean_id)
        .order_by(CoffeeBean.name)
        .all()
    )


def add_stock(owner_id, bean_id, quantity_kg: Decimal) -> None:
    """Increment on-hand stock. Upsert, so two simultaneous deliveries cannot collide."""
    now = datetime.now(timezone.utc)
    stmt = pg_insert(OwnerStock).values(
        id=uuid.uuid4(),
        owner_id=owner_id,
        coffee_bean_id=bean_id,
        quantity_kg=quantity_kg,
        updated_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_owner_stock",
        set_={"quantity_kg": OwnerStock.quantity_kg + quantity_kg, "updated_at": now},
    )
    db.session.execute(stmt)


def set_stock(owner_id, bean_id, quantity_kg: Decimal) -> OwnerStock:
    """Manual adjustment: overwrite the on-hand quantity."""
    if db.session.get(CoffeeBean, bean_id) is None:
        raise ServiceError("Bean not found.", 404)

    now = datetime.now(timezone.utc)
    stmt = pg_insert(OwnerStock).values(
        id=uuid.uuid4(),
        owner_id=owner_id,
        coffee_bean_id=bean_id,
        quantity_kg=quantity_kg,
        updated_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_owner_stock",
        set_={"quantity_kg": quantity_kg, "updated_at": now},
    )
    db.session.execute(stmt)
    db.session.commit()
    return OwnerStock.query.filter_by(owner_id=owner_id, coffee_bean_id=bean_id).one()
