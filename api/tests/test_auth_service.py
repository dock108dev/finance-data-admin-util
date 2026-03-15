"""Tests for the auth service — JWT tokens, password hashing."""

from datetime import timedelta
from unittest.mock import patch

import pytest

from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_magic_token,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "secure-password-123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_different_hashes(self):
        p = "same-password"
        h1 = hash_password(p)
        h2 = hash_password(p)
        # bcrypt generates different salts
        assert h1 != h2
        assert verify_password(p, h1) is True
        assert verify_password(p, h2) is True


class TestJWTTokens:
    def test_create_access_token(self):
        with patch("app.services.auth.get_settings") as mock:
            mock.return_value.jwt_secret = "test-secret"
            token = create_access_token(1, "test@example.com", "admin")
            assert isinstance(token, str)
            assert len(token) > 20

    def test_decode_valid_token(self):
        with patch("app.services.auth.get_settings") as mock:
            mock.return_value.jwt_secret = "test-secret"
            token = create_access_token(42, "user@example.com", "viewer")
            payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["email"] == "user@example.com"
        assert payload["role"] == "viewer"
        assert payload["type"] == "access"

    def test_decode_expired_token(self):
        with patch("app.services.auth.get_settings") as mock:
            mock.return_value.jwt_secret = "test-secret"
            token = create_access_token(1, "test@example.com", "admin",
                                         expires_delta=timedelta(seconds=-1))
            payload = decode_token(token)

        assert payload is None

    def test_decode_invalid_token(self):
        with patch("app.services.auth.get_settings") as mock:
            mock.return_value.jwt_secret = "test-secret"
            payload = decode_token("invalid.token.string")

        assert payload is None

    def test_decode_wrong_secret(self):
        with patch("app.services.auth.get_settings") as mock:
            mock.return_value.jwt_secret = "secret-1"
            token = create_access_token(1, "test@example.com", "admin")

        with patch("app.services.auth.get_settings") as mock:
            mock.return_value.jwt_secret = "secret-2"
            payload = decode_token(token)

        assert payload is None

    def test_create_refresh_token(self):
        with patch("app.services.auth.get_settings") as mock:
            mock.return_value.jwt_secret = "test-secret"
            token = create_refresh_token(42)
            payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "refresh"

    def test_custom_expiry(self):
        with patch("app.services.auth.get_settings") as mock:
            mock.return_value.jwt_secret = "test-secret"
            token = create_access_token(1, "a@b.com", "admin",
                                         expires_delta=timedelta(hours=48))
            payload = decode_token(token)

        assert payload is not None


class TestMagicToken:
    def test_generate(self):
        token = generate_magic_token()
        assert isinstance(token, str)
        assert len(token) > 20

    def test_unique(self):
        t1 = generate_magic_token()
        t2 = generate_magic_token()
        assert t1 != t2
