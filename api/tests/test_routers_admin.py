"""Tests for admin router endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest


def _mock_scalars(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


class TestTriggerTask:
    @pytest.mark.asyncio
    async def test_valid_task_returns_200(self, client, auth_headers):
        resp = await client.post(
            "/api/admin/tasks/trigger",
            json={"task_name": "ingest_daily_prices"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_name"] == "ingest_daily_prices"
        assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_invalid_task_returns_400(self, client, auth_headers):
        resp = await client.post(
            "/api/admin/tasks/trigger",
            json={"task_name": "nonexistent_task"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_auth_required(self, client):
        resp = await client.post(
            "/api/admin/tasks/trigger",
            json={"task_name": "ingest_daily_prices"},
        )
        assert resp.status_code == 401


class TestGetTaskRegistry:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, auth_headers):
        resp = await client.get("/api/admin/tasks/registry", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_all_tasks(self, client, auth_headers):
        resp = await client.get("/api/admin/tasks/registry", headers=auth_headers)
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 11

    @pytest.mark.asyncio
    async def test_task_has_required_fields(self, client, auth_headers):
        resp = await client.get("/api/admin/tasks/registry", headers=auth_headers)
        task = resp.json()[0]
        assert "name" in task
        assert "description" in task
        assert "params" in task
        assert "asset_classes" in task


class TestListScrapeRuns:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/admin/tasks/runs", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_by_type(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/admin/tasks/runs?scraper_type=price_ingest", headers=auth_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_by_status(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/admin/tasks/runs?status=completed", headers=auth_headers
        )
        assert resp.status_code == 200


class TestListPipelineJobs:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/admin/pipeline/jobs", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_by_phase(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/admin/pipeline/jobs?phase=price_ingestion_stocks",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestRunPipeline:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, auth_headers, mock_db_session):
        resp = await client.post("/api/admin/pipeline/1/run", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["asset_id"] == 1
        assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_with_session_date(self, client, auth_headers, mock_db_session):
        resp = await client.post(
            "/api/admin/pipeline/1/run?session_date=2024-01-15",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["session_date"] == "2024-01-15"


class TestListDataConflicts:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/admin/data/conflicts", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_by_type(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/admin/data/conflicts?conflict_type=duplicate_candle",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_unresolved_only(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/admin/data/conflicts?unresolved_only=true", headers=auth_headers
        )
        assert resp.status_code == 200


class TestTriggerExchangeSync:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, auth_headers):
        resp = await client.post("/api/admin/exchange/sync", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_custom_asset_class(self, client, auth_headers):
        resp = await client.post(
            "/api/admin/exchange/sync?asset_class=STOCKS", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["asset_class"] == "STOCKS"
