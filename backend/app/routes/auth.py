from flask import Blueprint, request, jsonify, g, current_app
from pydantic import ValidationError
from datetime import datetime, timezone

from ..extensions import db, limiter
from ..models import User, OwnerProfile, Supplier
from ..services.google_auth import verify_google_token
from ..services.jwt_service import create_token, decode_token
from ..decorators import require_auth
from ..responses import service_error
from ..services import guest_service
from ..services.errors import ServiceError
from ..schemas.auth import GoogleLoginRequest, OnboardRequest

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/google")
@limiter.limit("30 per minute")
def google_login():
    """Verify a Google ID token, upsert the user, return an app JWT."""
    try:
        body = GoogleLoginRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 422

    try:
        claims = verify_google_token(body.credential)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 401

    user = User.query.filter_by(google_sub=claims["google_sub"]).first()
    if user is None:
        user = User(
            google_sub=claims["google_sub"],
            email=claims["email"],
            name=claims["name"],
            avatar_url=claims["avatar_url"],
        )
        db.session.add(user)
    else:
        # Keep name and avatar fresh
        user.name = claims["name"]
        user.avatar_url = claims["avatar_url"]
        user.updated_at = datetime.now(timezone.utc)

    db.session.commit()

    token = create_token(str(user.id), user.role)
    return jsonify({"token": token, "user": user.to_dict()}), 200


@auth_bp.post("/guest")
@limiter.limit(lambda: current_app.config["GUEST_RATE_LIMIT"], key_func=guest_service.client_ip)
def guest_login():
    """
    Fallback sign-in for when Google is unavailable. Creates a throwaway account
    and returns the same shape as /auth/google. The guest then onboards like anyone else.
    404 when the feature flag is off, as if the route did not exist.
    """
    if not current_app.config["GUEST_LOGIN_ENABLED"]:
        return jsonify({"error": "Not found."}), 404

    try:
        user = guest_service.create_guest(guest_service.client_ip())
    except ServiceError as exc:
        return service_error(exc)

    token = create_token(str(user.id), None, is_guest=True)
    claims = decode_token(token)
    return jsonify({
        "token": token,
        "user": user.to_dict(),
        "guest": {
            "expires_at": datetime.fromtimestamp(claims["exp"], tz=timezone.utc).isoformat(),
            "token_ttl_hours": current_app.config["GUEST_JWT_TTL_HOURS"],
            "purge_after_hours": current_app.config["GUEST_PURGE_AFTER_HOURS"],
        },
    }), 200


@auth_bp.get("/me")
@require_auth
def me():
    """Return the current authenticated user's profile."""
    user = g.current_user
    payload = user.to_dict()

    if user.role == "OWNER" and user.owner_profile:
        payload["profile"] = user.owner_profile.to_dict()
    elif user.role == "SUPPLIER" and user.supplier_profile:
        payload["profile"] = user.supplier_profile.to_dict()

    return jsonify(payload), 200


@auth_bp.post("/onboard")
@require_auth
@limiter.limit("10 per minute", key_func=lambda: str(g.current_user.id))
def onboard():
    """Set the user's role once. Returns 409 if already onboarded."""
    user = g.current_user

    if user.role is not None:
        return jsonify({"error": "Already onboarded."}), 409

    try:
        body = OnboardRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 422

    user.role = body.role
    user.updated_at = datetime.now(timezone.utc)

    if body.role == "OWNER":
        profile = OwnerProfile(
            user_id=user.id,
            business_name=body.business_name,
        )
        db.session.add(profile)
    else:
        profile = Supplier(
            user_id=user.id,
            company_name=body.company_name,
            location=body.location,
            contact_email=body.contact_email,
            website=body.website,
        )
        db.session.add(profile)

    db.session.commit()

    # Issue a fresh token that now carries the role. A guest keeps the expiry they
    # already had, so onboarding cannot be used to stretch a guest session.
    expires_at = (
        datetime.fromtimestamp(g.token_claims["exp"], tz=timezone.utc) if user.is_guest else None
    )
    token = create_token(str(user.id), user.role, is_guest=user.is_guest, expires_at=expires_at)
    return jsonify({"token": token, "user": user.to_dict()}), 201
