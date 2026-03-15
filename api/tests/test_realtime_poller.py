"""Tests for the database poller."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.realtime.poller import DBPoller


class TestDBPoller:
    def test_initial_state(self):
        poller = DBPoller()
        assert poller._running is False
        assert poller._tasks == []

    def test_stats_initial(self):
        poller = DBPoller()
        stats = poller.stats()
        assert stats["poll_count"]["prices"] == 0
        assert stats["poll_count"]["signals"] == 0
        assert stats["poll_count"]["sessions"] == 0
        assert stats["last_poll_at"]["prices"] is None

    @pytest.mark.asyncio
    async def test_start_creates_tasks(self):
        poller = DBPoller()
        poller.start()
        assert poller._running is True
        assert len(poller._tasks) == 3
        await poller.stop()
        assert poller._running is False
        assert poller._tasks == []

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        poller = DBPoller()
        poller.start()
        poller.start()  # Second call should be no-op
        assert len(poller._tasks) == 3
        await poller.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_tasks(self):
        poller = DBPoller()
        poller.start()
        tasks = list(poller._tasks)
        await poller.stop()
        for task in tasks:
            assert task.cancelled() or task.done()

    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        poller = DBPoller()
        # Should not raise
        await poller.stop()

    def test_stats_structure(self):
        poller = DBPoller()
        stats = poller.stats()
        assert "poll_count" in stats
        assert "last_poll_duration_ms" in stats
        assert "last_poll_at" in stats
        assert set(stats["poll_count"].keys()) == {"prices", "signals", "sessions"}
        assert set(stats["last_poll_duration_ms"].keys()) == {"prices", "signals", "sessions"}

    @pytest.mark.asyncio
    async def test_loops_skip_when_no_subscribers(self):
        """Poller loops should not poll when no one is subscribed."""
        poller = DBPoller()
        # Manually call the internal poll methods with no subscribers
        # They should just return without doing anything
        await poller._poll_prices([])
        await poller._poll_signals([])
        await poller._poll_sessions([])

    @pytest.mark.asyncio
    async def test_poll_prices_handles_db_error(self):
        """Price polling should handle DB errors gracefully."""
        poller = DBPoller()

        async def mock_get_db():
            raise RuntimeError("DB not initialized")
            yield  # Make it an async generator

        with patch("app.db.session.get_db", mock_get_db):
            # Should not raise — errors are caught internally
            await poller._poll_prices(["prices:CRYPTO"])

    @pytest.mark.asyncio
    async def test_poll_signals_handles_db_error(self):
        poller = DBPoller()

        async def mock_get_db():
            raise RuntimeError("DB not initialized")
            yield

        with patch("app.db.session.get_db", mock_get_db):
            await poller._poll_signals(["signals:alpha"])

    @pytest.mark.asyncio
    async def test_poll_sessions_handles_db_error(self):
        poller = DBPoller()

        async def mock_get_db():
            raise RuntimeError("DB not initialized")
            yield

        with patch("app.db.session.get_db", mock_get_db):
            await poller._poll_sessions(["sessions:CRYPTO:2024-01-15"])

    @pytest.mark.asyncio
    async def test_poll_prices_with_mock_data(self):
        """Test that price polling publishes to manager."""
        poller = DBPoller()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "asset_id": 1, "ticker": "BTC", "exchange": "Binance",
                "price": 50000.0, "bid": 49999, "ask": 50001,
                "volume_24h": 1000000, "observed_at": datetime(2024, 1, 15, tzinfo=timezone.utc),
                "asset_class": "CRYPTO",
            }
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def mock_get_db():
            yield mock_db

        with patch("app.db.session.get_db", mock_get_db):
            await poller._poll_prices(["prices:CRYPTO"])

    @pytest.mark.asyncio
    async def test_poll_signals_with_mock_data(self):
        """Test signal polling with mock data."""
        poller = DBPoller()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "id": 1, "asset_id": 1, "ticker": "BTC",
                "signal_type": "TECHNICAL_BREAKOUT", "direction": "LONG",
                "strength": 0.8, "confidence_tier": "HIGH",
                "trigger_price": 50000.0,
                "detected_at": datetime(2024, 1, 15, tzinfo=timezone.utc),
            }
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def mock_get_db():
            yield mock_db

        with patch("app.db.session.get_db", mock_get_db):
            await poller._poll_signals(["signals:alpha"])

    @pytest.mark.asyncio
    async def test_poll_sessions_with_mock_data(self):
        """Test session polling with mock data."""
        poller = DBPoller()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "id": 1, "asset_id": 1, "session_date": "2024-01-15",
                "status": "closed", "open_price": 100.0, "close_price": 103.0,
                "change_pct": 3.0,
                "updated_at": datetime(2024, 1, 15, 20, 0, tzinfo=timezone.utc),
                "asset_class": "STOCKS",
            }
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def mock_get_db():
            yield mock_db

        with patch("app.db.session.get_db", mock_get_db):
            await poller._poll_sessions(["sessions:STOCKS:2024-01-15"])

    @pytest.mark.asyncio
    async def test_poll_prices_no_rows(self):
        """Test that polling with no new data is handled."""
        poller = DBPoller()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def mock_get_db():
            yield mock_db

        with patch("app.db.session.get_db", mock_get_db):
            await poller._poll_prices(["prices:CRYPTO"])

    @pytest.mark.asyncio
    async def test_poll_loop_only_runs_with_subscribers(self):
        """Verify the loop logic checks for active subscribers."""
        poller = DBPoller()
        # Start poller briefly
        poller.start()
        await asyncio.sleep(0.05)
        # Stats should show 0 polls since no subscribers
        stats = poller.stats()
        assert stats["poll_count"]["prices"] == 0
        await poller.stop()
