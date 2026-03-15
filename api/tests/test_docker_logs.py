"""Tests for the Docker logs endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDockerLogs:
    @pytest.mark.asyncio
    async def test_invalid_container(self, client, auth_headers):
        resp = await client.get(
            "/api/admin/logs",
            params={"container": "hacker-container"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "allow list" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_auth_required(self, client):
        resp = await client.get("/api/admin/logs", params={"container": "fin-api"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_container_relay_unavailable(self, client, auth_headers):
        with patch("app.routers.docker_logs.httpx.AsyncClient") as mock_client_cls:
            import httpx
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client_cls.return_value = mock_client

            resp = await client.get(
                "/api/admin/logs",
                params={"container": "fin-api"},
                headers=auth_headers,
            )
        assert resp.status_code == 503
        assert "relay" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_valid_container_success(self, client, auth_headers):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {
            "container": "fin-api",
            "lines": 100,
            "logs": "2024-01-15T10:00:00Z INFO startup\n2024-01-15T10:00:01Z INFO ready",
        }

        with patch("app.routers.docker_logs.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            resp = await client.get(
                "/api/admin/logs",
                params={"container": "fin-api", "lines": 100},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["container"] == "fin-api"
        assert "startup" in data["logs"]

    @pytest.mark.asyncio
    async def test_container_not_found(self, client, auth_headers):
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("app.routers.docker_logs.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            resp = await client.get(
                "/api/admin/logs",
                params={"container": "fin-api"},
                headers=auth_headers,
            )
        assert resp.status_code == 404
