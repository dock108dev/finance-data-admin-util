"""Tests for realtime authentication."""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.realtime.auth import _check_api_key, verify_ws_api_key, verify_sse_api_key


class TestCheckApiKey:
    def test_valid_key(self):
        with patch("app.realtime.auth.get_settings") as mock:
            mock.return_value.api_key = "secret-key"
            mock.return_value.environment = "production"
            assert _check_api_key("secret-key", client_label="test") is True

    def test_invalid_key(self):
        with patch("app.realtime.auth.get_settings") as mock:
            mock.return_value.api_key = "secret-key"
            mock.return_value.environment = "production"
            assert _check_api_key("wrong-key", client_label="test") is False

    def test_no_key_provided(self):
        with patch("app.realtime.auth.get_settings") as mock:
            mock.return_value.api_key = "secret-key"
            mock.return_value.environment = "production"
            assert _check_api_key(None, client_label="test") is False

    def test_dev_mode_allows_no_key_when_no_api_key_set(self):
        with patch("app.realtime.auth.get_settings") as mock:
            mock.return_value.api_key = ""
            mock.return_value.environment = "development"
            assert _check_api_key(None, client_label="test") is True

    def test_prod_mode_rejects_no_key(self):
        with patch("app.realtime.auth.get_settings") as mock:
            mock.return_value.api_key = ""
            mock.return_value.environment = "production"
            assert _check_api_key(None, client_label="test") is False


class TestVerifyWSApiKey:
    @pytest.mark.asyncio
    async def test_key_from_query_param(self):
        ws = MagicMock()
        ws.query_params = {"api_key": "secret-key"}
        ws.headers = {}

        with patch("app.realtime.auth.get_settings") as mock:
            mock.return_value.api_key = "secret-key"
            mock.return_value.environment = "production"
            result = await verify_ws_api_key(ws)
            assert result is True

    @pytest.mark.asyncio
    async def test_key_from_header(self):
        ws = MagicMock()
        ws.query_params = {}
        ws.headers = {"x-api-key": "secret-key"}

        with patch("app.realtime.auth.get_settings") as mock:
            mock.return_value.api_key = "secret-key"
            mock.return_value.environment = "production"
            result = await verify_ws_api_key(ws)
            assert result is True

    @pytest.mark.asyncio
    async def test_no_key(self):
        ws = MagicMock()
        ws.query_params = {}
        ws.headers = {}

        with patch("app.realtime.auth.get_settings") as mock:
            mock.return_value.api_key = "secret-key"
            mock.return_value.environment = "production"
            result = await verify_ws_api_key(ws)
            assert result is False


class TestVerifySSEApiKey:
    @pytest.mark.asyncio
    async def test_valid_key(self):
        request = MagicMock()
        request.query_params = {"api_key": "secret-key"}
        request.headers = {}

        with patch("app.realtime.auth.get_settings") as mock:
            mock.return_value.api_key = "secret-key"
            mock.return_value.environment = "production"
            # Should not raise
            await verify_sse_api_key(request)

    @pytest.mark.asyncio
    async def test_invalid_key_raises(self):
        from fastapi import HTTPException
        request = MagicMock()
        request.query_params = {}
        request.headers = {}

        with patch("app.realtime.auth.get_settings") as mock:
            mock.return_value.api_key = "secret-key"
            mock.return_value.environment = "production"
            with pytest.raises(HTTPException) as exc_info:
                await verify_sse_api_key(request)
            assert exc_info.value.status_code == 401
