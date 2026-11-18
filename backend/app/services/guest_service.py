"""
Guest accounts: a fallback sign-in for when Google is unavailable.

A guest is a normal users row (is_guest = true, no google_sub) that then goes
through the normal onboarding. Nothing here relaxes authorization: every
role check and ownership scope applies to a guest exactly as to anyone else.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import logging
import uuid
from datetime import datetime, timedelta, timezone

from flask import current_app, request
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Order, Supplier, User
from . import order_service
from .errors import ServiceError

log = logging.getLogger(__name__)

GUEST_NAME = "Guest"
GUEST_EMAIL_DOMAIN = "guest.labeans.local"

# Orders whose beans are still reserved. DELIVERED stock has left the supplier for good.
RESERVING_STATUSES = ("PENDING", "CONFIRMED", "PREPARING", "READY", "SHIPPED")
_PURGE_LOCK_KEY = 727_001


# Client IP ------------------------------------------------------------------

def _valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def client_ip() -> str:
    """
    The visitor's IP. Auth.js calls this API from the Next.js server, so the
    socket address is the frontend's, not the visitor's. The frontend forwards
    the real address in X-Client-IP together with a shared secret; the header
    is believed only when that secret matches, so it cannot be spoofed.
    """
    secret = current_app.config.get("GUEST_PROXY_SECRET") or ""
    if secret:
        supplied = request.headers.get("X-Internal-Secret", "")
        if hmac.compare_digest(supplied.encode(), secret.encode()):
            forwarded = request.headers.get("X-Client-IP", "").strip()
            if forwarded and _valid_ip(forwarded):
                return forwarded
    return request.remote_addr or "unknown"


def hash_ip(ip: str) -> str:
    """Keyed hash, so a database dump does not contain visitor IP addresses."""
    key = current_app.config["SECRET_KEY"].encode()
    return hmac.new(key, ip.encode(), hashlib.sha256).hexdigest()


# Creating guests ------------------------------------------------------------

def create_guest(ip: str) -> User:
    ip_hash = hash_ip(ip)
    cap = current_app.config["GUEST_MAX_PER_IP_PER_DAY"]
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    for _ in range(3):
        # One creation at a time per network, so the daily cap is exact under concurrency
        db.session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": ip_hash})
        recent = User.query.filter(
            User.is_guest.is_(True),
            User.guest_ip_hash == ip_hash,
            User.created_at >= since,
        ).count()
        if recent >= cap:
            db.session.rollback()
            raise ServiceError(
                "Too many guest accounts have been created from your network today. "
                "Try again tomorrow, or sign in with Google.",
                429,
            )

        user = User(
            google_sub=None,
            email=f"guest-{uuid.uuid4().hex[:12]}@{GUEST_EMAIL_DOMAIN}",
            name=GUEST_NAME,
            is_guest=True,
            guest_ip_hash=ip_hash,
        )
        db.session.add(user)
        try:
            db.session.commit()
            return user
        except IntegrityError:  # astronomically unlikely email collision
            db.session.rollback()

    raise ServiceError("Could not create a guest account. Please try again.", 503)


# Purging guests -------------------------------------------------------------

def _purge_one(user_id, cutoff: datetime) -> bool:
    """
    Delete one guest and everything they own. Returns True if open orders had
    stock released.

    Dependent rows (owner_profiles, suppliers, coffee_beans, blends, blend_items,
    presets, feedback, ai_generations, owner_stock, orders, order_items and
    owner-scoped knowledge_chunks) go with the user through ON DELETE CASCADE.
    Two things the cascade cannot do are handled here:

    * Open orders hold stock reserved on the supplier's beans. Deleting the order
      would leak that stock for good, so it is released first.
    * orders.supplier_id is RESTRICT, so orders addressed to a guest supplier are
      removed before the supplier. (Visibility rules mean there should be none.)
    """
    released = False
    open_orders = (
        Order.query
        .filter(Order.owner_id == user_id, Order.status.in_(RESERVING_STATUSES))
        .order_by(Order.id)
        .all()
    )
    for order in open_orders:
        order_service.release_stock(order)
        released = True

    supplier = Supplier.query.filter_by(user_id=user_id).first()
    if supplier is not None:
        db.session.execute(delete(Order).where(Order.supplier_id == supplier.id))

    # Re-check the conditions in the DELETE itself: never touch a real or a newer account
    db.session.execute(
        delete(User).where(User.id == user_id, User.is_guest.is_(True), User.created_at < cutoff)
    )
    db.session.commit()
    return released


def purge_guests(older_than_hours: float, *, dry_run: bool = False, limit: int | None = None) -> dict:
    """
    Delete guest accounts created more than older_than_hours ago.

    Safe to schedule: a Postgres advisory lock stops overlapping runs, each user
    is deleted in its own transaction (one failure does not block the rest), and
    only rows with is_guest = true are ever matched.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
    summary = {
        "cutoff": cutoff.isoformat(),
        "dry_run": dry_run,
        "matched": 0,
        "purged": 0,
        "orders_released": 0,
        "failed": 0,
        "skipped_locked": False,
    }

    with db.engine.connect() as lock_conn:
        if not lock_conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": _PURGE_LOCK_KEY}).scalar():
            summary["skipped_locked"] = True
            return summary
        try:
            query = (
                select(User.id)
                .where(User.is_guest.is_(True), User.created_at < cutoff)
                .order_by(User.created_at)
            )
            if limit:
                query = query.limit(limit)
            ids = list(db.session.execute(query).scalars())
            db.session.rollback()  # end the read transaction before deleting
            summary["matched"] = len(ids)
            if dry_run:
                return summary

            for user_id in ids:
                try:
                    if _purge_one(user_id, cutoff):
                        summary["orders_released"] += 1
                    summary["purged"] += 1
                except Exception:
                    db.session.rollback()
                    summary["failed"] += 1
                    log.exception("Could not purge guest %s", user_id)
            return summary
        finally:
            lock_conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _PURGE_LOCK_KEY})
