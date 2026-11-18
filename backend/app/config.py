import os
from dotenv import load_dotenv

load_dotenv()


def _normalise_db_url(url: str) -> str:
    """
    Hosts hand out postgres:// or postgresql:// URLs. SQLAlchemy 2.1 maps a bare
    postgresql:// to psycopg (v3), but this project ships psycopg2, so name the
    driver explicitly.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class Base:
    SECRET_KEY: str = os.environ["SECRET_KEY"]
    DATABASE_URL: str = _normalise_db_url(os.environ["DATABASE_URL"])
    SQLALCHEMY_DATABASE_URI: str = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET: str = os.environ["JWT_SECRET"]
    JWT_EXPIRES_HOURS: int = int(os.getenv("JWT_EXPIRES_HOURS", "24"))
    GOOGLE_CLIENT_ID: str = os.environ["GOOGLE_CLIENT_ID"]
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000"
    ).split(",")
    DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "USD")
    # Beans below this stock level flip from AVAILABLE to LOW_STOCK
    LOW_STOCK_KG: float = float(os.getenv("LOW_STOCK_KG", "20"))
    # "Reorder soon" shows when the first bean to run out is closer than this
    REORDER_THRESHOLD_DAYS: float = float(os.getenv("REORDER_THRESHOLD_DAYS", "10"))
    RATELIMIT_ENABLED: bool = os.getenv("RATELIMIT_ENABLED", "true").lower() != "false"

    # Guest login (fallback when Google sign-in is unavailable) ------------------
    # Lifetime of a guest's app JWT, and how long guest data is kept before the purge job removes it
    GUEST_JWT_TTL_HOURS: float = float(os.getenv("GUEST_JWT_TTL_HOURS", "4"))
    GUEST_PURGE_AFTER_HOURS: float = float(os.getenv("GUEST_PURGE_AFTER_HOURS", "24"))
    # Abuse and cost controls
    GUEST_RATE_LIMIT: str = os.getenv("GUEST_RATE_LIMIT", "5 per minute")        # /auth/guest, per IP
    GUEST_MAX_PER_IP_PER_DAY: int = int(os.getenv("GUEST_MAX_PER_IP_PER_DAY", "10"))
    GUEST_AI_LIMIT: str = os.getenv("GUEST_AI_LIMIT", "3 per minute;30 per day")  # /ai/*, per guest
    # A guest owner may only order from seeded demo suppliers (google_sub starts with the prefix)
    GUEST_ORDER_DEMO_SUPPLIERS_ONLY: bool = _flag("GUEST_ORDER_DEMO_SUPPLIERS_ONLY", True)
    DEMO_SUPPLIER_SUB_PREFIX: str = os.getenv("DEMO_SUPPLIER_SUB_PREFIX", "seed_")
    # The Next.js server forwards the visitor's IP in X-Client-IP. It is believed only when the
    # request also carries this secret in X-Internal-Secret; otherwise the socket address is used.
    GUEST_PROXY_SECRET: str = os.getenv("GUEST_PROXY_SECRET", "")


class Development(Base):
    DEBUG = True
    GUEST_LOGIN_ENABLED: bool = _flag("GUEST_LOGIN_ENABLED", True)


class Production(Base):
    DEBUG = False
    GUEST_LOGIN_ENABLED: bool = _flag("GUEST_LOGIN_ENABLED", False)


config_map = {
    "development": Development,
    "production": Production,
    "testing": Development,
}
