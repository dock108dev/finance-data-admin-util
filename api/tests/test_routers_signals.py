"""Tests for signals router endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest


def _mock_scalars(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _mock_scalar_one(item):
    result = MagicMock()
    result.scalar_one_or_none.return_value = item
    return result


class TestListAlphaSignals:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/signals/alpha", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_signal_type(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/signals/alpha?signal_type=CROSS_EXCHANGE_ARB", headers=auth_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_confidence(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/signals/alpha?confidence_tier=HIGH", headers=auth_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_direction(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/signals/alpha?direction=LONG", headers=auth_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_min_strength(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/signals/alpha?min_strength=0.5", headers=auth_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_outcome(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/signals/alpha?outcome=HIT", headers=auth_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_required(self, client):
        resp = await client.get("/api/signals/alpha")
        assert resp.status_code == 401


class TestListArbitrage:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/signals/arbitrage", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_asset_id(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/signals/arbitrage?asset_id=1", headers=auth_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_min_arb_pct(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/signals/arbitrage?min_arb_pct=0.5", headers=auth_headers
        )
        assert resp.status_code == 200


class TestListSentiment:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/signals/sentiment", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_asset_id(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/signals/sentiment?asset_id=1", headers=auth_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_asset_class_id(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get(
            "/api/signals/sentiment?asset_class_id=1", headers=auth_headers
        )
        assert resp.status_code == 200


class TestGetAnalysis:
    @pytest.mark.asyncio
    async def test_returns_200_when_found(self, client, auth_headers, mock_db_session):
        fake = MagicMock()
        fake.id = 1
        fake.asset_id = 1
        fake.analysis_date = "2024-01-15"
        fake.summary = "Bullish session"
        fake.key_moments_json = {}
        fake.narrative_blocks_json = {}
        fake.generated_by = "openai-gpt-4o"
        fake.generated_at = "2024-01-15T12:00:00Z"
        mock_db_session.execute = AsyncMock(return_value=_mock_scalar_one(fake))
        resp = await client.get("/api/signals/analysis/1", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalar_one(None))
        resp = await client.get("/api/signals/analysis/999", headers=auth_headers)
        assert resp.status_code == 404
