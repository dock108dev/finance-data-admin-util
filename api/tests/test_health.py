"""Tests for health check, diagnostics, and realtime status endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthz_returns_ok(self, client):
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")
        assert data["app"] == "ok"

    @pytest.mark.asyncio
    async def test_healthz_no_auth_required(self, client):
        # No auth headers needed
        resp = await client.get("/healthz")
        assert resp.status_code == 200


class TestDiagnostics:
    @pytest.mark.asyncio
    async def test_diagnostics_requires_auth(self, client):
        resp = await client.get("/api/diagnostics")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_diagnostics_returns_info(self, client, auth_headers):
        resp = await client.get("/api/diagnostics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "realtime" in data
        assert "poller" in data

    @pytest.mark.asyncio
    async def test_diagnostics_realtime_structure(self, client, auth_headers):
        resp = await client.get("/api/diagnostics", headers=auth_headers)
        data = resp.json()
        rt = data["realtime"]
        assert "boot_epoch" in rt
        assert "total_connections" in rt
        assert "total_channels" in rt
        assert "publish_count" in rt


class TestRealtimeStatus:
    @pytest.mark.asyncio
    async def test_realtime_status_requires_auth(self, client):
        resp = await client.get("/v1/realtime/status")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_realtime_status_returns_info(self, client, auth_headers):
        resp = await client.get("/v1/realtime/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "boot_epoch" in data
        assert "total_connections" in data
        assert "poller" in data
        assert "poll_count" in data["poller"]
