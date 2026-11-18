import jwt
from datetime import datetime, timedelta, timezone
from flask import current_app


def create_token(
    user_id: str,
    role: str | None,
    *,
    is_guest: bool = False,
    expires_at: datetime | None = None,
) -> str:
    """
    HS256 app JWT. Guests get a shorter lifetime and an is_guest claim.

    expires_at pins the expiry explicitly. Onboarding uses it so that issuing a
    fresh token never stretches a guest's session beyond what it was given.
    The role and is_guest claims are hints only; the API reloads the user.
    """
    now = datetime.now(timezone.utc)
    if expires_at is None:
        hours = (
            current_app.config["GUEST_JWT_TTL_HOURS"]
            if is_guest
            else current_app.config["JWT_EXPIRES_HOURS"]
        )
        expires_at = now + timedelta(hours=hours)

    payload = {"sub": user_id, "role": role, "iat": now, "exp": expires_at}
    if is_guest:
        payload["is_guest"] = True
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        current_app.config["JWT_SECRET"],
        algorithms=["HS256"],
        options={"require": ["sub", "exp", "iat"]},
    )
