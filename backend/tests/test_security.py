"""
Cross-user access (IDOR), role gating and owner-scoped retrieval.

Rule from the blueprint: another user's id must return 404 (never 403, never
the data), and a wrong role must return 403.
"""
import uuid

import pytest

pytestmark = pytest.mark.usefixtures("app")

MISSING = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def world(client, make, ai):
    owner_a = make.user("OWNER", "Owner A")
    owner_b = make.user("OWNER", "Owner B")
    sup_a = make.user("SUPPLIER", "Supplier A")
    sup_b = make.user("SUPPLIER", "Supplier B")

    bean_1 = make.bean(sup_a["supplier_id"], "Bean 1", stock="100")
    bean_2 = make.bean(sup_a["supplier_id"], "Bean 2", stock="100")
    blend = make.blend(owner_a["id"], [(bean_1, 60), (bean_2, 40)], name="A's blend")

    preset = client.post("/api/presets", json={"name": "A preset"}, headers=owner_a["headers"]).get_json()["id"]
    order = client.post(
        "/api/orders",
        json={"items": [{"coffee_bean_id": bean_1, "quantity_kg": 5}]},
        headers=owner_a["headers"],
    ).get_json()["items"][0]["id"]

    from app.extensions import db
    from app.models import AIGeneration

    with client.application.app_context():
        gen = AIGeneration(owner_id=uuid.UUID(owner_a["id"]), kind="GENERATE", input={}, status="OK")
        db.session.add(gen)
        db.session.commit()
        generation = str(gen.id)

    return dict(owner_a=owner_a, owner_b=owner_b, sup_a=sup_a, sup_b=sup_b,
                bean=bean_1, blend=blend, preset=preset, order=order, generation=generation)


# IDOR: user B asks for user A's id -> 404 ---------------------------------------

def test_supplier_cannot_touch_another_suppliers_bean(client, world):
    h = world["sup_b"]["headers"]
    bean = world["bean"]
    assert client.get(f"/api/supplier/beans/{bean}", headers=h).status_code == 404
    assert client.patch(f"/api/supplier/beans/{bean}", json={"stock_kg": 0}, headers=h).status_code == 404
    assert client.delete(f"/api/supplier/beans/{bean}", headers=h).status_code == 404
    assert client.get(f"/api/coffee-beans/{bean}", headers=h).status_code == 404
    # the owner-facing catalogue still shows it
    assert client.get(f"/api/coffee-beans/{bean}", headers=world["owner_b"]["headers"]).status_code == 200


def test_owner_cannot_touch_another_owners_blend(client, world):
    h, blend = world["owner_b"]["headers"], world["blend"]
    assert client.get(f"/api/blends/{blend}", headers=h).status_code == 404
    assert client.patch(f"/api/blends/{blend}", json={"name": "stolen"}, headers=h).status_code == 404
    assert client.post(f"/api/blends/{blend}/status", json={"status": "ARCHIVED"}, headers=h).status_code == 404
    assert client.post(f"/api/blends/{blend}/duplicate", headers=h).status_code == 404
    assert client.get(f"/api/blends/{blend}/feedback", headers=h).status_code == 404
    feedback = dict(overall=3, flavor=3, body=3, acidity=3, sweetness=3, brew_context="milk")
    assert client.post(f"/api/blends/{blend}/feedback", json=feedback, headers=h).status_code == 404
    assert client.post(f"/api/blends/{blend}/reorder", json={"total_kg": 5}, headers=h).status_code == 404
    assert client.post("/api/ai/substitute", json={"blend_id": blend}, headers=h).status_code == 404
    assert client.get("/api/blends", headers=h).get_json()["total"] == 0


def test_owner_cannot_touch_another_owners_preset(client, world):
    h, preset = world["owner_b"]["headers"], world["preset"]
    assert client.patch(f"/api/presets/{preset}", json={"name": "x"}, headers=h).status_code == 404
    assert client.delete(f"/api/presets/{preset}", headers=h).status_code == 404
    assert client.get("/api/presets", headers=h).get_json()["items"] == []


def test_owner_cannot_read_another_owners_generation(client, world):
    path = f"/api/ai/generations/{world['generation']}"
    assert client.get(path, headers=world["owner_b"]["headers"]).status_code == 404
    assert client.get(path, headers=world["owner_a"]["headers"]).status_code == 200


def test_orders_are_visible_only_to_the_two_parties(client, world):
    path = f"/api/orders/{world['order']}"
    for stranger in (world["owner_b"], world["sup_b"]):
        assert client.get(path, headers=stranger["headers"]).status_code == 404
        resp = client.patch(f"{path}/status", json={"status": "CANCELLED"}, headers=stranger["headers"])
        assert resp.status_code == 404
    assert client.get(path, headers=world["owner_a"]["headers"]).status_code == 200
    assert client.get(path, headers=world["sup_a"]["headers"]).status_code == 200


def test_a_strangers_failed_cancel_does_not_release_stock(client, make, world):
    before = make.stock_of(world["bean"])
    client.patch(f"/api/orders/{world['order']}/status", json={"status": "CANCELLED"},
                 headers=world["owner_b"]["headers"])
    assert make.stock_of(world["bean"]) == before


def test_owner_stock_and_insights_are_per_owner(client, world):
    a, b = world["owner_a"]["headers"], world["owner_b"]["headers"]
    client.patch("/api/owner-stock", json={"coffee_bean_id": world["bean"], "quantity_kg": 9}, headers=a)
    assert len(client.get("/api/owner-stock", headers=a).get_json()["items"]) == 1
    assert client.get("/api/owner-stock", headers=b).get_json()["items"] == []

    spend_b = client.get("/api/insights/spend", headers=b).get_json()["items"]
    assert all(m["amount"] == 0 for m in spend_b)
    summary_b = client.get("/api/dashboard/summary", headers=b).get_json()
    assert summary_b["active_orders"] == 0 and summary_b["month_spend"] == 0


# Role gating -> 403, no token -> 401 ----------------------------------------------

OWNER_ONLY = [
    ("get", "/api/blends"), ("post", "/api/blends"), ("get", "/api/presets"),
    ("post", "/api/orders"), ("get", "/api/dashboard/summary"),
    ("get", "/api/insights/spend"), ("get", "/api/insights/volume"), ("get", "/api/insights/reorder"),
    ("get", "/api/owner-stock"), ("patch", "/api/owner-stock"),
    ("post", "/api/ai/generate-blend"), ("post", "/api/ai/substitute"),
    ("post", "/api/ai/chat"), ("post", "/api/ai/analyze-feedback"),
    ("get", "/api/suppliers"),
]
SUPPLIER_ONLY = [("get", "/api/supplier/beans"), ("post", "/api/supplier/beans")]


@pytest.mark.parametrize("method,path", OWNER_ONLY)
def test_supplier_is_forbidden_from_owner_routes(client, world, method, path):
    resp = getattr(client, method)(path, json={}, headers=world["sup_a"]["headers"])
    assert resp.status_code == 403


@pytest.mark.parametrize("method,path", SUPPLIER_ONLY)
def test_owner_is_forbidden_from_supplier_routes(client, world, method, path):
    resp = getattr(client, method)(path, json={}, headers=world["owner_a"]["headers"])
    assert resp.status_code == 403


@pytest.mark.parametrize("method,path", OWNER_ONLY + SUPPLIER_ONLY + [("get", "/api/orders")])
def test_requests_without_a_token_are_401(client, method, path):
    assert getattr(client, method)(path, json={}).status_code == 401


def test_supplier_cannot_create_blends_or_orders_for_owners(client, world):
    resp = client.post("/api/orders",
                       json={"items": [{"coffee_bean_id": world["bean"], "quantity_kg": 1}]},
                       headers=world["sup_a"]["headers"])
    assert resp.status_code == 403


# Validation and error shape -----------------------------------------------------

def test_recipe_summing_to_99_is_a_clean_422(client, world):
    payload = {
        "name": "Short",
        "items": [{"coffee_bean_id": world["bean"], "percentage": 60},
                  {"coffee_bean_id": str(uuid.uuid4()), "percentage": 39}],
    }
    resp = client.post("/api/blends", json=payload, headers=world["owner_a"]["headers"])
    assert resp.status_code == 422
    assert resp.is_json


def test_unknown_route_returns_json_404(client):
    resp = client.get("/api/nope")
    assert resp.status_code == 404
    assert resp.is_json and "error" in resp.get_json()


# Retrieval scope ----------------------------------------------------------------

def test_retrieval_never_returns_another_owners_private_chunks(client, app, world):
    """Feedback comments are private to their author; global knowledge is shared."""
    from app.extensions import db
    from app.models import KnowledgeChunk
    from app.services import rag_service

    feedback = dict(overall=2, flavor=2, body=3, acidity=1, sweetness=3, brew_context="milk",
                    comment="Way too acidic in lattes")
    resp = client.post(f"/api/blends/{world['blend']}/feedback", json=feedback, headers=world["owner_a"]["headers"])
    assert resp.status_code == 201

    with app.app_context():
        db.session.add(KnowledgeChunk(
            owner_id=None, source_type="DOC", content="Global roasting notes",
            metadata_={}, embedding=[1.0] + [0.0] * 1535,
        ))
        db.session.commit()

        seen_by_a = {c.content for c in rag_service.retrieve("acidic", uuid.UUID(world["owner_a"]["id"]))}
        seen_by_b = {c.content for c in rag_service.retrieve("acidic", uuid.UUID(world["owner_b"]["id"]))}

    assert any("Way too acidic" in c for c in seen_by_a)
    assert "Global roasting notes" in seen_by_a
    assert seen_by_b == {"Global roasting notes"}
