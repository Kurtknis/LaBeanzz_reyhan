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


class Development(Base):
    DEBUG = True


class Production(Base):
    DEBUG = False


config_map = {
    "development": Development,
    "production": Production,
    "testing": Development,
}
