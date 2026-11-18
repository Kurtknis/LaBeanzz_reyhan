import threading
from decimal import Decimal

import pytest

pytestmark = pytest.mark.usefixtures("app")


@pytest.fixture
def world(make):
    """One owner, two suppliers with two beans each, and a second owner."""
    owner = make.user("OWNER", "Cafe One")
    other_owner = make.user("OWNER", "Cafe Two")
    sup_a = make.user("SUPPLIER", "Supplier A")
    sup_b = make.user("SUPPLIER", "Supplier B")
    return {
        "owner": owner,
        "other_owner": other_owner,
        "sup_a": sup_a,
        "sup_b": sup_b,
        "bean_a1": make.bean(sup_a["supplier_id"], "A1", stock="100", price="10.00"),
        "bean_a2": make.bean(sup_a["supplier_id"], "A2", stock="50", price="20.00"),
        "bean_b1": make.bean(sup_b["supplier_id"], "B1", stock="80", price="30.00"),
    }


def place(client, owner, items, **extra):
    return client.post(
        "/api/orders",
        json={"items": [{"coffee_bean_id": b, "quantity_kg": q} for b, q in items], **extra},
        headers=owner["headers"],
    )


def advance(client, supplier, order_id, status):
    return client.patch(f"/api/orders/{order_id}/status", json={"status": status}, headers=supplier["headers"])


# Creating orders ---------------------------------------------------------------

def test_order_reserves_stock_snapshots_price_and_computes_total(client, make, world):
    resp = place(client, world["owner"], [(world["bean_a1"], 10), (world["bean_a2"], 5)])
    assert resp.status_code == 201
    orders = resp.get_json()["items"]
    assert len(orders) == 1
    order = orders[0]
    assert order["status"] == "PENDING"
    assert order["total_price"] == 200.0          # 10*10 + 5*20
    assert order["currency"] == "USD"
    assert order["group_id"] is None
    assert {i["unit_price"] for i in order["items"]} == {10.0, 20.0}
    assert make.stock_of(world["bean_a1"]) == Decimal("90.00")
    assert make.stock_of(world["bean_a2"]) == Decimal("45.00")


def test_client_cannot_set_price_or_owner(client, make, world):
    resp = client.post(
        "/api/orders",
        json={
            "items": [{"coffee_bean_id": world["bean_a1"], "quantity_kg": 1, "unit_price": 0.01}],
            "owner_id": world["other_owner"]["id"],
            "total_price": 0,
        },
        headers=world["owner"]["headers"],
    )
    assert resp.status_code == 201
    order = resp.get_json()["items"][0]
    assert order["total_price"] == 10.0
    # The order belongs to the caller, not the owner id in the body
    assert client.get(f"/api/orders/{order['id']}", headers=world["other_owner"]["headers"]).status_code == 404


def test_orders_spanning_suppliers_are_split_and_grouped(client, world):
    resp = place(client, world["owner"], [(world["bean_a1"], 10), (world["bean_b1"], 10)])
    assert resp.status_code == 201
    orders = resp.get_json()["items"]
    assert len(orders) == 2
    assert orders[0]["group_id"] and orders[0]["group_id"] == orders[1]["group_id"]
    assert {o["supplier"]["id"] for o in orders} == {world["sup_a"]["supplier_id"], world["sup_b"]["supplier_id"]}


def test_ordering_more_than_stock_fails_clearly_and_changes_nothing(client, make, world):
    resp = place(client, world["owner"], [(world["bean_a1"], 5), (world["bean_a2"], 50.01)])
    assert resp.status_code == 409
    assert "A2" in resp.get_json()["error"]
    assert make.stock_of(world["bean_a1"]) == Decimal("100.00")
    assert make.stock_of(world["bean_a2"]) == Decimal("50.00")


def test_unavailable_bean_cannot_be_ordered(client, make, world):
    out = make.bean(world["sup_a"]["supplier_id"], "Gone", stock="0", status="OUT_OF_STOCK")
    assert place(client, world["owner"], [(out, 1)]).status_code == 409


def test_emptying_a_bean_marks_it_out_of_stock_and_low_stock_is_flagged(client, make, world):
    assert place(client, world["owner"], [(world["bean_a2"], 50)]).status_code == 201
    assert make.stock_of(world["bean_a2"]) == Decimal("0.00")
    assert make.status_of(world["bean_a2"]) == "OUT_OF_STOCK"

    assert place(client, world["owner"], [(world["bean_a1"], 85)]).status_code == 201   # 15 kg left
    assert make.status_of(world["bean_a1"]) == "LOW_STOCK"


@pytest.mark.parametrize("payload", [
    {"items": []},
    {"items": [{"coffee_bean_id": "not-a-uuid", "quantity_kg": 1}]},
    {"items": [{"coffee_bean_id": "00000000-0000-0000-0000-000000000000", "quantity_kg": 0}]},
    {"items": [{"coffee_bean_id": "00000000-0000-0000-0000-000000000000", "quantity_kg": -3}]},
])
def test_invalid_order_bodies_are_rejected_with_422(client, world, payload):
    resp = client.post("/api/orders", json=payload, headers=world["owner"]["headers"])
    assert resp.status_code == 422
    assert isinstance(resp.get_json()["error"], str)


def test_duplicate_beans_in_one_order_are_rejected(client, world):
    resp = place(client, world["owner"], [(world["bean_a1"], 1), (world["bean_a1"], 2)])
    assert resp.status_code == 422


def test_unknown_bean_is_404(client, world):
    resp = place(client, world["owner"], [("00000000-0000-0000-0000-000000000000", 1)])
    assert resp.status_code == 404


def test_concurrent_orders_never_oversell(client, app, make, world):
    """Two owners race for 60 kg each of a 100 kg bean: exactly one may win."""
    bean = make.bean(world["sup_a"]["supplier_id"], "Race", stock="100")
    results = []

    def worker(owner):
        with app.test_client() as c:
            results.append(place(c, owner, [(bean, 60)]).status_code)

    threads = [threading.Thread(target=worker, args=(o,)) for o in (world["owner"], world["other_owner"])]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(results) == [201, 409]
    assert make.stock_of(bean) == Decimal("40.00")


def test_many_concurrent_orders_keep_stock_non_negative(client, app, make, world):
    bean = make.bean(world["sup_a"]["supplier_id"], "Burst", stock="10")
    results = []

    def worker():
        with app.test_client() as c:
            results.append(place(c, world["owner"], [(bean, 3)]).status_code)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count(201) == 3          # 3 x 3 kg fits in 10 kg, a 4th does not
    assert make.stock_of(bean) == Decimal("1.00")


# Lifecycle ---------------------------------------------------------------------

def test_supplier_walks_the_order_forward_and_owner_completes(client, make, world):
    order_id = place(client, world["owner"], [(world["bean_a1"], 10)]).get_json()["items"][0]["id"]
    for status in ("CONFIRMED", "PREPARING", "READY", "SHIPPED", "DELIVERED"):
        resp = advance(client, world["sup_a"], order_id, status)
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()["status"] == status

    done = client.patch(f"/api/orders/{order_id}/status", json={"status": "COMPLETED"},
                        headers=world["owner"]["headers"])
    assert done.status_code == 200
    assert done.get_json()["status"] == "COMPLETED"


@pytest.mark.parametrize("target", ["PREPARING", "DELIVERED", "PENDING", "CANCELLED"])
def test_supplier_cannot_jump_or_cancel(client, world, target):
    order_id = place(client, world["owner"], [(world["bean_a1"], 1)]).get_json()["items"][0]["id"]
    assert advance(client, world["sup_a"], order_id, target).status_code == 409


def test_owner_cannot_advance_fulfilment_or_complete_early(client, world):
    order_id = place(client, world["owner"], [(world["bean_a1"], 1)]).get_json()["items"][0]["id"]
    for target in ("CONFIRMED", "COMPLETED", "DELIVERED"):
        resp = client.patch(f"/api/orders/{order_id}/status", json={"status": target},
                            headers=world["owner"]["headers"])
        assert resp.status_code == 409


def test_cancelling_releases_reserved_stock_and_restores_availability(client, make, world):
    order_id = place(client, world["owner"], [(world["bean_a2"], 50)]).get_json()["items"][0]["id"]
    assert make.status_of(world["bean_a2"]) == "OUT_OF_STOCK"

    resp = client.patch(f"/api/orders/{order_id}/status", json={"status": "CANCELLED"},
                        headers=world["owner"]["headers"])
    assert resp.status_code == 200
    assert make.stock_of(world["bean_a2"]) == Decimal("50.00")
    assert make.status_of(world["bean_a2"]) == "AVAILABLE"


def test_cancel_after_confirmation_is_allowed_but_not_after_preparing(client, make, world):
    order_id = place(client, world["owner"], [(world["bean_a1"], 10)]).get_json()["items"][0]["id"]
    advance(client, world["sup_a"], order_id, "CONFIRMED")
    cancel = client.patch(f"/api/orders/{order_id}/status", json={"status": "CANCELLED"},
                          headers=world["owner"]["headers"])
    assert cancel.status_code == 200
    assert make.stock_of(world["bean_a1"]) == Decimal("100.00")

    second = place(client, world["owner"], [(world["bean_a1"], 10)]).get_json()["items"][0]["id"]
    advance(client, world["sup_a"], second, "CONFIRMED")
    advance(client, world["sup_a"], second, "PREPARING")
    late = client.patch(f"/api/orders/{second}/status", json={"status": "CANCELLED"},
                        headers=world["owner"]["headers"])
    assert late.status_code == 409


def test_cancelled_order_cannot_be_cancelled_twice_or_release_stock_twice(client, make, world):
    order_id = place(client, world["owner"], [(world["bean_a1"], 10)]).get_json()["items"][0]["id"]
    body = {"status": "CANCELLED"}
    assert client.patch(f"/api/orders/{order_id}/status", json=body, headers=world["owner"]["headers"]).status_code == 200
    assert client.patch(f"/api/orders/{order_id}/status", json=body, headers=world["owner"]["headers"]).status_code == 409
    assert make.stock_of(world["bean_a1"]) == Decimal("100.00")


def test_delivery_adds_to_owner_stock(client, world):
    order_id = place(client, world["owner"], [(world["bean_a1"], 12), (world["bean_a2"], 3)]).get_json()["items"][0]["id"]
    for status in ("CONFIRMED", "PREPARING", "READY", "SHIPPED"):
        advance(client, world["sup_a"], order_id, status)

    assert client.get("/api/owner-stock", headers=world["owner"]["headers"]).get_json()["items"] == []
    advance(client, world["sup_a"], order_id, "DELIVERED")

    stock = {r["name"]: r["quantity_kg"] for r in
             client.get("/api/owner-stock", headers=world["owner"]["headers"]).get_json()["items"]}
    assert stock == {"A1": 12.0, "A2": 3.0}


def test_a_second_delivery_accumulates(client, world):
    for _ in range(2):
        order_id = place(client, world["owner"], [(world["bean_a1"], 5)]).get_json()["items"][0]["id"]
        for status in ("CONFIRMED", "PREPARING", "READY", "SHIPPED", "DELIVERED"):
            advance(client, world["sup_a"], order_id, status)
    items = client.get("/api/owner-stock", headers=world["owner"]["headers"]).get_json()["items"]
    assert items[0]["quantity_kg"] == 10.0


def test_supplier_can_set_eta_when_advancing(client, world):
    order_id = place(client, world["owner"], [(world["bean_a1"], 1)]).get_json()["items"][0]["id"]
    resp = client.patch(f"/api/orders/{order_id}/status",
                        json={"status": "CONFIRMED", "eta_date": "2026-12-01"},
                        headers=world["sup_a"]["headers"])
    assert resp.get_json()["eta_date"] == "2026-12-01"


# Visibility --------------------------------------------------------------------

def test_supplier_sees_only_their_orders_and_no_owner_blend_data(client, make, world):
    blend = make.blend(world["owner"]["id"], [(world["bean_a1"], 50), (world["bean_b1"], 50)], name="Secret Recipe")
    resp = client.post(f"/api/blends/{blend}/reorder", json={"total_kg": 20}, headers=world["owner"]["headers"])
    assert resp.status_code == 201

    for supplier, other in ((world["sup_a"], world["sup_b"]), (world["sup_b"], world["sup_a"])):
        listing = client.get("/api/orders", headers=supplier["headers"]).get_json()
        assert listing["total"] == 1
        order = listing["items"][0]
        assert order["supplier"]["id"] == supplier["supplier_id"]
        assert "source_blend_id" not in order and "group_id" not in order
        assert "Secret Recipe" not in str(order)
        assert order["owner"]["business_name"] == "Cafe One"

        # And the other supplier cannot open it
        assert client.get(f"/api/orders/{order['id']}", headers=other["headers"]).status_code == 404


def test_owner_lists_only_their_own_orders(client, world):
    place(client, world["owner"], [(world["bean_a1"], 1)])
    place(client, world["other_owner"], [(world["bean_a1"], 2)])
    mine = client.get("/api/orders", headers=world["owner"]["headers"]).get_json()
    assert mine["total"] == 1
    assert mine["items"][0]["items"][0]["quantity_kg"] == 1.0


def test_active_filter_splits_open_and_finished_orders(client, world):
    open_id = place(client, world["owner"], [(world["bean_a1"], 1)]).get_json()["items"][0]["id"]
    done_id = place(client, world["owner"], [(world["bean_a1"], 1)]).get_json()["items"][0]["id"]
    client.patch(f"/api/orders/{done_id}/status", json={"status": "CANCELLED"}, headers=world["owner"]["headers"])

    active = client.get("/api/orders?active=true", headers=world["owner"]["headers"]).get_json()["items"]
    past = client.get("/api/orders?active=false", headers=world["owner"]["headers"]).get_json()["items"]
    assert [o["id"] for o in active] == [open_id]
    assert [o["id"] for o in past] == [done_id]


def test_unknown_status_filter_is_rejected(client, world):
    assert client.get("/api/orders?status=BOGUS", headers=world["owner"]["headers"]).status_code == 422


# Reorder from a blend ----------------------------------------------------------

def test_reorder_splits_quantity_by_percentage(client, make, world):
    blend = make.blend(world["owner"]["id"], [(world["bean_a1"], 60), (world["bean_a2"], 40)])
    resp = client.post(f"/api/blends/{blend}/reorder", json={"total_kg": 10}, headers=world["owner"]["headers"])
    assert resp.status_code == 201
    order = resp.get_json()["items"][0]
    assert order["source_blend_id"] == blend
    assert {i["name"]: i["quantity_kg"] for i in order["items"]} == {"A1": 6.0, "A2": 4.0}
    assert order["total_price"] == 6 * 10 + 4 * 20


def test_reorder_across_suppliers_creates_grouped_orders(client, make, world):
    blend = make.blend(world["owner"]["id"], [(world["bean_a1"], 50), (world["bean_b1"], 50)])
    orders = client.post(f"/api/blends/{blend}/reorder", json={"total_kg": 10},
                         headers=world["owner"]["headers"]).get_json()["items"]
    assert len(orders) == 2
    assert orders[0]["group_id"] == orders[1]["group_id"] is not None


def test_reorder_fails_cleanly_when_a_bean_is_short(client, make, world):
    blend = make.blend(world["owner"]["id"], [(world["bean_a1"], 50), (world["bean_a2"], 50)])
    resp = client.post(f"/api/blends/{blend}/reorder", json={"total_kg": 200}, headers=world["owner"]["headers"])
    assert resp.status_code == 409
    assert make.stock_of(world["bean_a1"]) == Decimal("100.00")


def test_deleting_a_bean_that_has_orders_is_a_clean_409(client, make, world):
    place(client, world["owner"], [(world["bean_a1"], 1)])
    resp = client.delete(f"/api/supplier/beans/{world['bean_a1']}", headers=world["sup_a"]["headers"])
    assert resp.status_code == 409
    assert "cannot be deleted" in resp.get_json()["error"]
