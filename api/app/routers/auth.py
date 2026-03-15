"""Authentication endpoints — signup, login, token refresh.

Equivalent to sports-data-admin's auth.py router.
"""

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.users import User
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


# ── Dependencies ────────────────────────────────────────────────────────────

async def get_current_user_dep(
    db: AsyncSession = Depends(get_db),
) -> User:
    """Placeholder dependency — in production, extract user from JWT.

    For now, returns the first admin user or raises 401.
    This is wired up when jwt_secret is configured.
    """
    raise HTTPException(status_code=401, detail="Not authenticated")


# ── Request / Response Models ───────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str | None
    role: str
    is_active: bool
    last_login_at: str | None

    model_config = {"from_attributes": True}


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse)
async def signup(
    request: SignupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user account."""
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create user
    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        display_name=request.display_name,
        role="viewer",  # Default role
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()

    # Generate tokens
    access = create_access_token(user.id, user.email, user.role)
    refresh = create_refresh_token(user.id)

    logger.info("auth.signup", email=user.email, user_id=user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user_id=user.id,
        email=user.email,
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email and password."""
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    access = create_access_token(user.id, user.email, user.role)
    refresh = create_refresh_token(user.id)

    logger.info("auth.login", email=user.email, user_id=user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user_id=user.id,
        email=user.email,
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh an access token using a refresh token."""
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or disabled")

    access = create_access_token(user.id, user.email, user.role)
    refresh = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user_id=user.id,
        email=user.email,
        role=user.role,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user: User = Depends(get_current_user_dep),
):
    """Get the current authenticated user's profile."""
    return user
