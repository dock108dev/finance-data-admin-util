"""Tests for market data router endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest


def _mock_scalars(items):
    """Helper: make db.execute() return a mock with scalars().all() -> items."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _mock_scalar_one(item):
    """Helper: make db.execute() return scalar_one_or_none() -> item."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = item
    return result


class TestListAssets:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/markets/assets", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_filters_by_asset_class(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/markets/assets?asset_class=STOCKS", headers=auth_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_pagination(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/markets/assets?limit=10&offset=5", headers=auth_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_required(self, client):
        resp = await client.get("/api/markets/assets")
        assert resp.status_code == 401


class TestGetAsset:
    @pytest.mark.asyncio
    async def test_returns_200_when_found(self, client, auth_headers, mock_db_session):
        fake = MagicMock()
        fake.id = 1
        fake.asset_class_code = "STOCKS"
        fake.ticker = "AAPL"
        fake.name = "Apple"
        fake.sector = "Technology"
        fake.industry = None
        fake.market_cap = 3e12
        fake.exchange = "NASDAQ"
        fake.is_active = True
        fake.last_price_at = None
        mock_db_session.execute = AsyncMock(return_value=_mock_scalar_one(fake))
        resp = await client.get("/api/markets/assets/1", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalar_one(None))
        resp = await client.get("/api/markets/assets/999", headers=auth_headers)
        assert resp.status_code == 404


class TestListSessions:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/markets/sessions", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filters_by_asset_id(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/markets/sessions?asset_id=1", headers=auth_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filters_by_date_range(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/markets/sessions?start_date=2024-01-01&end_date=2024-12-31",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filters_by_status(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/markets/sessions?status=closed", headers=auth_headers
        )
        assert resp.status_code == 200


class TestGetSession:
    @pytest.mark.asyncio
    async def test_returns_200_when_found(self, client, auth_headers, mock_db_session):
        fake = MagicMock()
        fake.id = 1
        fake.asset_id = 1
        fake.session_date = "2024-01-15"
        fake.open_price = 100.0
        fake.high_price = 105.0
        fake.low_price = 99.0
        fake.close_price = 103.0
        fake.volume = 1e6
        fake.change_pct = 3.0
        fake.status = "closed"
        mock_db_session.execute = AsyncMock(return_value=_mock_scalar_one(fake))
        resp = await client.get("/api/markets/sessions/1", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalar_one(None))
        resp = await client.get("/api/markets/sessions/999", headers=auth_headers)
        assert resp.status_code == 404


class TestGetCandles:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/markets/candles/1", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_interval_parameter(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/markets/candles/1?interval=1h", headers=auth_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_date_range(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/markets/candles/1?start=2024-01-01T00:00:00&end=2024-01-02T00:00:00",
            headers=auth_headers,
        )
        assert resp.status_code == 200
