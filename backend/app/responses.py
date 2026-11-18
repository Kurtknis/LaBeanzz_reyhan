from flask import jsonify
from pydantic import ValidationError

from .services.errors import ServiceError


def validation_error(exc: ValidationError):
    """422 response with a readable message and per-field details."""
    fields: dict[str, str] = {}
    for err in exc.errors(include_context=False, include_url=False, include_input=False):
        loc = ".".join(str(p) for p in err["loc"]) or "body"
        fields.setdefault(loc, err["msg"])
    message = "; ".join(f"{k}: {v}" for k, v in fields.items())
    return jsonify({"error": message or "Invalid request.", "fields": fields}), 422


def service_error(exc: ServiceError):
    return jsonify({"error": exc.message}), exc.status
