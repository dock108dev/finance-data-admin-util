"""Tests for auth router endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_user(user_id=1, email="test@example.com", role="viewer", is_active=True):
    """Create a mock User object."""
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.role = role
    user.is_active = is_active
    user.hashed_password = "$2b$12$mockhashedpasswordhere"
    user.display_name = "Test User"
    user.last_login_at = None
    return user


class TestSignup:
    @pytest.mark.asyncio
    async def test_signup_success(self, client, mock_db_session):
        # No existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Capture added user and set id on flush
        added_users = []
        def capture_add(obj):
            obj.id = 99
            added_users.append(obj)
        mock_db_session.add = capture_add
        mock_db_session.flush = AsyncMock()

        with patch("app.routers.auth.hash_password", return_value="hashed"), \
             patch("app.routers.auth.create_access_token", return_value="access-token"), \
             patch("app.routers.auth.create_refresh_token", return_value="refresh-token"):
            resp = await client.post("/api/auth/signup", json={
                "email": "new@example.com",
                "password": "password123",
                "display_name": "New User",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "access-token"
        assert data["refresh_token"] == "refresh-token"
        assert data["token_type"] == "bearer"
        assert data["user_id"] == 99

    @pytest.mark.asyncio
    async def test_signup_duplicate_email(self, client, mock_db_session):
        existing_user = _mock_user()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        resp = await client.post("/api/auth/signup", json={
            "email": "test@example.com",
            "password": "password123",
        })
        assert resp.status_code == 409


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client, mock_db_session):
        user = _mock_user()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.flush = AsyncMock()

        with patch("app.routers.auth.verify_password", return_value=True), \
             patch("app.routers.auth.create_access_token", return_value="access-tok"), \
             patch("app.routers.auth.create_refresh_token", return_value="refresh-tok"):
            resp = await client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password123",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "access-tok"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, mock_db_session):
        user = _mock_user()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.routers.auth.verify_password", return_value=False):
            resp = await client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "wrong",
            })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client, mock_db_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        resp = await client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "password123",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_disabled_account(self, client, mock_db_session):
        user = _mock_user(is_active=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.routers.auth.verify_password", return_value=True):
            resp = await client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password123",
            })
        assert resp.status_code == 403


class TestRefresh:
    @pytest.mark.asyncio
    async def test_refresh_success(self, client, mock_db_session):
        user = _mock_user()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.routers.auth.decode_token", return_value={"sub": "1", "type": "refresh"}), \
             patch("app.routers.auth.create_access_token", return_value="new-access"), \
             patch("app.routers.auth.create_refresh_token", return_value="new-refresh"):
            resp = await client.post("/api/auth/refresh", json={
                "refresh_token": "old-refresh-token",
            })

        assert resp.status_code == 200
        assert resp.json()["access_token"] == "new-access"

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client, mock_db_session):
        with patch("app.routers.auth.decode_token", return_value=None):
            resp = await client.post("/api/auth/refresh", json={
                "refresh_token": "invalid-token",
            })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_wrong_type(self, client, mock_db_session):
        with patch("app.routers.auth.decode_token", return_value={"sub": "1", "type": "access"}):
            resp = await client.post("/api/auth/refresh", json={
                "refresh_token": "access-token-not-refresh",
            })
        assert resp.status_code == 401


class TestGetMe:
    @pytest.mark.asyncio
    async def test_me_requires_auth(self, client):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401
