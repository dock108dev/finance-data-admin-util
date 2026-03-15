"""Tests for API key authentication dependency."""

import pytest


class TestRequireApiKey:
    @pytest.mark.asyncio
    async def test_valid_key_passes(self, client, auth_headers):
        resp = await client.get("/api/admin/tasks/registry", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_key_returns_401(self, client):
        resp = await client.get("/api/admin/tasks/registry")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_key_returns_401(self, client):
        resp = await client.get(
            "/api/admin/tasks/registry",
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_healthz_bypasses_auth(self, client):
        resp = await client.get("/healthz")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_required_on_markets(self, client):
        resp = await client.get("/api/markets/assets")
        assert resp.status_code == 401
