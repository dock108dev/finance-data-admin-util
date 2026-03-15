"""Authentication service — JWT tokens, password hashing, user management.

Equivalent to sports-data-admin's auth service.
"""

import secrets
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Password Hashing ───────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain, hashed)


# ── JWT Tokens ──────────────────────────────────────────────────────────────

def create_access_token(
    user_id: int,
    email: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    expires = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))

    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expires,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_refresh_token(user_id: int) -> str:
    """Create a long-lived refresh token."""
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(days=30)

    payload = {
        "sub": str(user_id),
        "exp": expires,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token.

    Returns the payload dict or None if invalid/expired.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ── Magic Links ─────────────────────────────────────────────────────────────

def generate_magic_token() -> str:
    """Generate a secure random token for magic link auth."""
    return secrets.token_urlsafe(32)
