"""Tests for extended admin endpoints — resolve conflicts, backfill, bulk ops."""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestResolveConflict:
    @pytest.mark.asyncio
    async def test_resolve_success(self, client, auth_headers, mock_db_session):
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        resp = await client.post(
            "/api/admin/data/conflicts/1/resolve",
            headers=auth_headers,
            json={"resolution_notes": "Fixed duplicate data"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_resolve_not_found(self, client, auth_headers, mock_db_session):
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        resp = await client.post(
            "/api/admin/data/conflicts/999/resolve",
            headers=auth_headers,
            json={"resolution_notes": "N/A"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_resolve_auth_required(self, client):
        resp = await client.post(
            "/api/admin/data/conflicts/1/resolve",
            json={"resolution_notes": "test"},
        )
        assert resp.status_code == 401


class TestBackfill:
    @pytest.mark.asyncio
    async def test_backfill_success(self, client, auth_headers):
        resp = await client.post(
            "/api/admin/backfill",
            headers=auth_headers,
            json={
                "task_name": "ingest_daily_prices",
                "asset_class": "STOCKS",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert data["task_name"] == "ingest_daily_prices"

    @pytest.mark.asyncio
    async def test_backfill_invalid_task(self, client, auth_headers):
        resp = await client.post(
            "/api/admin/backfill",
            headers=auth_headers,
            json={"task_name": "invalid_task"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_backfill_auth_required(self, client):
        resp = await client.post("/api/admin/backfill", json={"task_name": "ingest_daily_prices"})
        assert resp.status_code == 401


class TestBulkPipeline:
    @pytest.mark.asyncio
    async def test_bulk_success(self, client, auth_headers):
        resp = await client.post(
            "/api/admin/pipeline/bulk",
            headers=auth_headers,
            json={"asset_ids": [1, 2, 3], "session_date": "2024-01-15"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert data["jobs_dispatched"] == 3

    @pytest.mark.asyncio
    async def test_bulk_too_many(self, client, auth_headers):
        resp = await client.post(
            "/api/admin/pipeline/bulk",
            headers=auth_headers,
            json={"asset_ids": list(range(51))},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_bulk_auth_required(self, client):
        resp = await client.post("/api/admin/pipeline/bulk", json={"asset_ids": [1]})
        assert resp.status_code == 401
