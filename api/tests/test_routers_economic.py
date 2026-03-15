"""Tests for economic indicator endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest


def _mock_scalars(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


class TestListIndicators:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/economic/indicators", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_by_series_id(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/economic/indicators",
            params={"series_id": "GDP"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_by_category(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/economic/indicators",
            params={"category": "employment"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_by_date_range(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/economic/indicators",
            params={"start_date": "2024-01-01", "end_date": "2024-12-31"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_required(self, client):
        resp = await client.get("/api/economic/indicators")
        assert resp.status_code == 401


class TestGetLatestIndicators:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/economic/latest", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_required(self, client):
        resp = await client.get("/api/economic/latest")
        assert resp.status_code == 401
