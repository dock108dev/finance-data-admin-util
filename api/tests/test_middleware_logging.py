"""Tests for structured logging middleware."""

from unittest.mock import patch

import pytest


class TestStructuredLoggingMiddleware:
    @pytest.mark.asyncio
    async def test_logs_request(self, client, auth_headers):
        with patch("app.middleware.logging.logger") as mock_logger:
            await client.get("/healthz")
            mock_logger.info.assert_called()
            call_kwargs = mock_logger.info.call_args
            assert call_kwargs[0][0] == "http.request"

    @pytest.mark.asyncio
    async def test_logs_method_and_path(self, client, auth_headers):
        with patch("app.middleware.logging.logger") as mock_logger:
            await client.get("/healthz")
            kwargs = mock_logger.info.call_args.kwargs
            assert kwargs["method"] == "GET"
            assert kwargs["path"] == "/healthz"

    @pytest.mark.asyncio
    async def test_logs_status_code(self, client, auth_headers):
        with patch("app.middleware.logging.logger") as mock_logger:
            await client.get("/healthz")
            kwargs = mock_logger.info.call_args.kwargs
            assert kwargs["status"] == 200

    @pytest.mark.asyncio
    async def test_logs_duration(self, client, auth_headers):
        with patch("app.middleware.logging.logger") as mock_logger:
            await client.get("/healthz")
            kwargs = mock_logger.info.call_args.kwargs
            assert "duration_ms" in kwargs
            assert isinstance(kwargs["duration_ms"], float)
