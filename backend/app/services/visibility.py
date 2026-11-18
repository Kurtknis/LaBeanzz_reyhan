"""
Which suppliers (and therefore which beans) an owner can see and order from.

* A regular owner sees real suppliers only. Guest suppliers' beans and profiles
  stay private to the guest who made them, so guest-written text never reaches a
  real owner's catalog, blends or AI prompts.
* A guest owner sees seeded demo suppliers only (GUEST_ORDER_DEMO_SUPPLIERS_ONLY),
  so a throwaway account cannot place orders with real suppliers. With the flag
  off they see the same real suppliers as everyone else.

Out of scope here: a supplier's own beans (those are scoped by supplier_id) and
orders (scoped by owner_id / supplier_id). This only narrows the shared catalog.
"""
from __future__ import annotations

import sqlalchemy as sa
from flask import current_app
from sqlalchemy.orm import aliased

from ..extensions import db
from ..models import Supplier, User


def visible_supplier_ids(user: User | None):
    """A SELECT of supplier ids, for use as `column.in_(...)`."""
    supplier = aliased(Supplier)
    account = aliased(User)

    query = (
        sa.select(supplier.id)
        .join(account, account.id == supplier.user_id)
        .where(account.is_guest.is_(False))
    )
    if user is None:
        return query.where(sa.false())

    if user.is_guest and current_app.config["GUEST_ORDER_DEMO_SUPPLIERS_ONLY"]:
        prefix = current_app.config["DEMO_SUPPLIER_SUB_PREFIX"]
        query = query.where(account.google_sub.startswith(prefix, autoescape=True))
    return query


def visible_supplier_ids_for(owner_id):
    """Same, for callers that only have the owner's id."""
    return visible_supplier_ids(db.session.get(User, owner_id))
