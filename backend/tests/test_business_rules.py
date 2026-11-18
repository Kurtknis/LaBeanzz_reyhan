from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.services import business_rules as rules


# Order status transitions -------------------------------------------------------

SUPPLIER_STEPS = [
    ("PENDING", "CONFIRMED"),
    ("CONFIRMED", "PREPARING"),
    ("PREPARING", "READY"),
    ("READY", "SHIPPED"),
    ("SHIPPED", "DELIVERED"),
]


@pytest.mark.parametrize("current,target", SUPPLIER_STEPS)
def test_supplier_moves_forward_one_step(current, target):
    assert rules.can_transition("SUPPLIER", current, target)


@pytest.mark.parametrize("current,target", [
    ("PENDING", "PREPARING"),      # skipping a step
    ("PENDING", "DELIVERED"),
    ("SHIPPED", "READY"),          # going backwards
    ("DELIVERED", "COMPLETED"),    # completing belongs to the owner
    ("PENDING", "CANCELLED"),      # cancelling belongs to the owner
    ("DELIVERED", "DELIVERED"),
    ("COMPLETED", "CONFIRMED"),
    ("CANCELLED", "CONFIRMED"),
])
def test_supplier_cannot_make_other_moves(current, target):
    assert not rules.can_transition("SUPPLIER", current, target)


@pytest.mark.parametrize("current", ["PENDING", "CONFIRMED"])
def test_owner_can_cancel_early(current):
    assert rules.can_transition("OWNER", current, "CANCELLED")


@pytest.mark.parametrize("current", ["PREPARING", "READY", "SHIPPED", "DELIVERED", "COMPLETED", "CANCELLED"])
def test_owner_cannot_cancel_late(current):
    assert not rules.can_transition("OWNER", current, "CANCELLED")


def test_owner_completes_only_after_delivery():
    assert rules.can_transition("OWNER", "DELIVERED", "COMPLETED")
    for current in ("PENDING", "CONFIRMED", "PREPARING", "READY", "SHIPPED"):
        assert not rules.can_transition("OWNER", current, "COMPLETED")


def test_owner_cannot_advance_fulfilment():
    assert not rules.can_transition("OWNER", "PENDING", "CONFIRMED")


def test_unknown_role_is_denied():
    assert not rules.can_transition("ADMIN", "PENDING", "CONFIRMED")


# Reordering a blend -------------------------------------------------------------

def test_split_by_percentage():
    parts = rules.split_by_percentage([("a", 60), ("b", 30), ("c", 10)], Decimal("50"))
    assert parts == [("a", Decimal("30.00")), ("b", Decimal("15.00")), ("c", Decimal("5.00"))]


def test_split_rounds_to_cents():
    parts = dict(rules.split_by_percentage([("a", 33), ("b", 67)], Decimal("10")))
    assert parts["a"] == Decimal("3.30")
    assert parts["b"] == Decimal("6.70")


# Reorder intelligence -----------------------------------------------------------

RECIPE = [("a", "Brazil Santos", 60), ("b", "Gayo Aceh", 40)]


def test_days_remaining_names_the_first_bean_to_run_out():
    # 2 kg/day: a uses 1.2 kg/day, b uses 0.8 kg/day
    stock = {"a": Decimal("12"), "b": Decimal("4")}
    days, bean = rules.days_remaining(RECIPE, stock, Decimal("2"))
    assert bean == "b"
    assert days == pytest.approx(5.0)


def test_missing_stock_counts_as_zero_days():
    days, bean = rules.days_remaining(RECIPE, {"a": Decimal("100")}, 2)
    assert days == 0
    assert bean == "b"


def test_no_usage_figure_means_no_estimate():
    assert rules.days_remaining(RECIPE, {"a": 10, "b": 10}, 0) is None
    assert rules.days_remaining(RECIPE, {"a": 10, "b": 10}, None) is None


def test_empty_recipe_has_no_estimate():
    assert rules.days_remaining([], {}, 2) is None


# Calendar -----------------------------------------------------------------------

def test_month_keys_cross_a_year_boundary():
    now = datetime(2027, 2, 10, tzinfo=timezone.utc)
    assert rules.month_keys(now, 4) == ["2026-11", "2026-12", "2027-01", "2027-02"]


def test_month_keys_single_month():
    assert rules.month_keys(datetime(2026, 11, 13, tzinfo=timezone.utc), 1) == ["2026-11"]
