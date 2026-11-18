import logging

from flask import Flask, jsonify
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException

from .config import config_map
from .extensions import db, migrate, cors, limiter


def _json_default(obj):
    # Pydantic puts the original exception in error context; render it as text
    # instead of failing the whole response with a 500.
    if isinstance(obj, Exception):
        return str(obj)
    return DefaultJSONProvider.default(obj)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(429)
    def too_many_requests(_exc):
        return jsonify({"error": "Too many requests. Please wait a moment and try again."}), 429

    @app.errorhandler(HTTPException)
    def http_error(exc: HTTPException):
        return jsonify({"error": exc.description or exc.name}), exc.code

    @app.errorhandler(Exception)
    def unexpected(exc: Exception):
        # Log the traceback server-side; never leak internals to the client
        app.logger.exception("Unhandled error: %s", exc)
        db.session.rollback()
        return jsonify({"error": "Something went wrong on our side. Please try again."}), 500


def create_app(env: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_map[env])
    app.json.default = _json_default
    logging.basicConfig(level=logging.INFO)

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )

    # Blueprints
    from .routes.health import health_bp
    from .routes.auth import auth_bp
    from .routes.coffee_beans import beans_bp
    from .routes.suppliers import suppliers_bp
    from .routes.ai import ai_bp
    from .routes.blends import blends_bp
    from .routes.orders import orders_bp
    from .routes.insights import insights_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(beans_bp, url_prefix="/api")
    app.register_blueprint(suppliers_bp, url_prefix="/api")
    app.register_blueprint(ai_bp, url_prefix="/api")
    app.register_blueprint(blends_bp, url_prefix="/api")
    app.register_blueprint(orders_bp, url_prefix="/api")
    app.register_blueprint(insights_bp, url_prefix="/api")

    _register_error_handlers(app)
    return app
