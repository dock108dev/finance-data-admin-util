"""Tests for the FastAPI application factory and lifespan."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI


class TestCreateApp:
    def test_returns_fastapi_instance(self):
        with patch("main.get_settings") as mock_gs:
            mock_gs.return_value.allowed_cors_origins = ["http://localhost:3000"]
            from main import create_app
            app = create_app()
            assert isinstance(app, FastAPI)

    def test_app_title(self):
        with patch("main.get_settings") as mock_gs:
            mock_gs.return_value.allowed_cors_origins = ["http://localhost:3000"]
            from main import create_app
            app = create_app()
            assert app.title == "Fin Data Admin API"

    def test_app_version(self):
        with patch("main.get_settings") as mock_gs:
            mock_gs.return_value.allowed_cors_origins = ["http://localhost:3000"]
            from main import create_app
            app = create_app()
            assert app.version == "0.2.0"

    def test_routers_registered(self):
        with patch("main.get_settings") as mock_gs:
            mock_gs.return_value.allowed_cors_origins = ["http://localhost:3000"]
            from main import create_app
            app = create_app()
            paths = [route.path for route in app.routes]
            assert any("/api/markets" in p for p in paths)
            assert any("/api/signals" in p for p in paths)
            assert any("/api/admin" in p for p in paths)


class TestHealthz:
    @pytest.mark.asyncio
    async def test_healthz_returns_200(self, client):
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")
        assert data["app"] == "ok"

    @pytest.mark.asyncio
    async def test_healthz_no_auth_required(self, client):
        resp = await client.get("/healthz")
        assert resp.status_code == 200


class TestLifespan:
    @pytest.mark.asyncio
    async def test_lifespan_calls_init_db(self):
        with patch("main.get_settings") as mock_gs, \
             patch("main.init_db", new_callable=AsyncMock) as mock_init:
            mock_gs.return_value.database_url = "postgresql+asyncpg://x/y"
            mock_gs.return_value.allowed_cors_origins = []

            from main import lifespan, create_app
            app = create_app()

            async with lifespan(app):
                pass

            mock_init.assert_awaited_once_with("postgresql+asyncpg://x/y")
