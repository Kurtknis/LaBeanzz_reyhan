"""
Test setup.

DB tests need a disposable Postgres with the pgvector extension:

    TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/labeans_test pytest

The database name must contain "test": the schema is dropped and rebuilt with
the real Alembic migrations. Without TEST_DATABASE_URL the DB tests are skipped
and only the pure business-rule tests run.
"""
import os
import uuid
from decimal import Decimal
from pathlib import Path

import pytest

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL")

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-test-jwt-secret-1234")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ["RATELIMIT_ENABLED"] = "true"   # limits are per user and every test makes fresh users
os.environ["DATABASE_URL"] = TEST_DB_URL or "postgresql://localhost/labeans_unused"

requires_db = pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DATABASE_URL is not set")


@pytest.fixture(scope="session")
def app():
    if not TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL is not set")
    from sqlalchemy.engine import make_url

    db_name = make_url(TEST_DB_URL).database or ""
    if "test" not in db_name:
        pytest.fail(f'Refusing to rebuild database "{db_name}": its name must contain "test".')

    from flask_migrate import upgrade
    from sqlalchemy import text

    from app import create_app
    from app.extensions import db

    application = create_app("testing")
    with application.app_context():
        db.session.execute(text("DROP SCHEMA public CASCADE"))
        db.session.execute(text("CREATE SCHEMA public"))
        db.session.commit()
        upgrade(directory=str(Path(__file__).resolve().parent.parent / "migrations"))
    return application


@pytest.fixture(autouse=True)
def _clean_tables(request):
    yield
    if "app" not in request.fixturenames:
        return
    from sqlalchemy import text

    from app.extensions import db

    application = request.getfixturevalue("app")
    with application.app_context():
        db.session.rollback()
        db.session.execute(text("TRUNCATE users, knowledge_chunks CASCADE"))
        db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


# Factories: each opens its own app context and returns plain ids -----------------

class Factory:
    def __init__(self, app):
        self.app = app

    def user(self, role: str, name: str = "Test"):
        from app.extensions import db
        from app.models import OwnerProfile, Supplier, User
        from app.services.jwt_service import create_token

        with self.app.app_context():
            user = User(
                google_sub=uuid.uuid4().hex,
                email=f"{uuid.uuid4().hex}@test.dev",
                name=name,
                role=role,
            )
            db.session.add(user)
            db.session.flush()
            supplier_id = None
            if role == "OWNER":
                db.session.add(OwnerProfile(user_id=user.id, business_name=name, taste_adjustments={}))
            else:
                supplier = Supplier(user_id=user.id, company_name=name)
                db.session.add(supplier)
                db.session.flush()
                supplier_id = str(supplier.id)
            db.session.commit()
            token = create_token(str(user.id), role)
            return {
                "id": str(user.id),
                "supplier_id": supplier_id,
                "headers": {"Authorization": f"Bearer {token}"},
            }

    def bean(self, supplier_id: str, name="Bean", stock="100", price="10.00",
             acidity=5, body=5, sweetness=5, status="AVAILABLE", story=None):
        from app.extensions import db
        from app.models import CoffeeBean

        with self.app.app_context():
            bean = CoffeeBean(
                supplier_id=uuid.UUID(supplier_id),
                name=name,
                origin="Brazil",
                roast_level="MEDIUM",
                flavor_notes=["cocoa"],
                acidity=acidity,
                body=body,
                sweetness=sweetness,
                price_per_kg=Decimal(price),
                stock_kg=Decimal(stock),
                status=status,
                producer_story=story,
            )
            db.session.add(bean)
            db.session.commit()
            return str(bean.id)

    def blend(self, owner_id: str, recipe: list[tuple[str, int]], name="Blend",
              status="DRAFT", daily_usage=None, style="espresso"):
        from app.extensions import db
        from app.models import Blend, BlendItem

        with self.app.app_context():
            blend = Blend(
                owner_id=uuid.UUID(owner_id), name=name, status=status, style=style,
                daily_usage_kg=Decimal(str(daily_usage)) if daily_usage is not None else None,
                predicted_profile={"computed": {"acidity": 5, "body": 5, "sweetness": 5}},
            )
            db.session.add(blend)
            db.session.flush()
            for bean_id, pct in recipe:
                db.session.add(BlendItem(blend_id=blend.id, coffee_bean_id=uuid.UUID(bean_id), percentage=pct))
            db.session.commit()
            return str(blend.id)

    def stock_of(self, bean_id: str) -> Decimal:
        from app.extensions import db
        from app.models import CoffeeBean

        with self.app.app_context():
            return db.session.get(CoffeeBean, uuid.UUID(bean_id)).stock_kg

    def status_of(self, bean_id: str) -> str:
        from app.extensions import db
        from app.models import CoffeeBean

        with self.app.app_context():
            return db.session.get(CoffeeBean, uuid.UUID(bean_id)).status


@pytest.fixture
def make(app):
    return Factory(app)


# Fake LLM / embeddings ---------------------------------------------------------

UNIT_VECTOR = [1.0] + [0.0] * 1535


class FakeAI:
    """Stands in for ai_service. Queue responses; the last one repeats."""

    def __init__(self):
        self.calls: list[list[dict]] = []
        self._responses: list = []

    def queue(self, *responses):
        self._responses = list(responses)

    def embed(self, texts):
        return [UNIT_VECTOR for _ in texts]

    def complete_json(self, messages, schema, model=None, temperature=0.3):
        self.calls.append(messages)
        if not self._responses:
            raise AssertionError("FakeAI was called without a queued response")
        response = self._responses.pop(0) if len(self._responses) > 1 else self._responses[0]
        if isinstance(response, Exception):
            raise response
        return response, 5


@pytest.fixture
def ai(monkeypatch):
    from app.services import ai_service

    fake = FakeAI()
    monkeypatch.setattr(ai_service, "embed", fake.embed)
    monkeypatch.setattr(ai_service, "complete_json", fake.complete_json)
    return fake
