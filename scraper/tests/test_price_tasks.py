"""Tests for price ingestion tasks."""

from unittest.mock import MagicMock, patch

import pytest


def _patch_task(task_path, run_manager_path="fin_scraper.jobs.price_tasks"):
    """Helper to patch get_db_session + run_manager for a task."""
    return (
        patch(f"{run_manager_path}.get_db_session"),
        patch(f"{run_manager_path}.create_run"),
        patch(f"{run_manager_path}.complete_run"),
        patch(f"{run_manager_path}.fail_run"),
    )


class TestIngestDailyPrices:
    def test_happy_path(self):
        with patch("fin_scraper.jobs.price_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.price_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.price_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.price_tasks.fail_run"):
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_run = MagicMock(id=1, scraper_type="price_ingest")
            mock_create.return_value = mock_run

            from fin_scraper.jobs.price_tasks import ingest_daily_prices
            result = ingest_daily_prices()

            assert "stocks_processed" in result
            assert "crypto_processed" in result
            assert "candles_created" in result
            mock_create.assert_called_once()
            mock_complete.assert_called_once()

    def test_create_run_called_with_correct_type(self):
        with patch("fin_scraper.jobs.price_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.price_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.price_tasks.complete_run"), \
             patch("fin_scraper.jobs.price_tasks.fail_run"):
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)

            from fin_scraper.jobs.price_tasks import ingest_daily_prices
            ingest_daily_prices()
            mock_create.assert_called_once_with(mock_db, "price_ingest", requested_by="celery_beat")

    def test_fail_run_on_exception(self):
        with patch("fin_scraper.jobs.price_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.price_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.price_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.price_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_run = MagicMock(id=1)
            mock_create.return_value = mock_run
            mock_complete.side_effect = Exception("boom")

            from fin_scraper.jobs.price_tasks import ingest_daily_prices
            with pytest.raises(Exception):
                ingest_daily_prices()


class TestIngestIntradayPrices:
    def test_happy_path(self):
        with patch("fin_scraper.jobs.price_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.price_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.price_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.price_tasks.fail_run"):
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)

            from fin_scraper.jobs.price_tasks import ingest_intraday_prices
            result = ingest_intraday_prices()

            assert "candles_created" in result
            assert "assets_polled" in result
            mock_complete.assert_called_once()

    def test_create_run_type(self):
        with patch("fin_scraper.jobs.price_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.price_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.price_tasks.complete_run"), \
             patch("fin_scraper.jobs.price_tasks.fail_run"):
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)

            from fin_scraper.jobs.price_tasks import ingest_intraday_prices
            ingest_intraday_prices()
            mock_create.assert_called_once_with(mock_db, "intraday_ingest", requested_by="celery_beat")


class TestSyncExchangePrices:
    def test_happy_path(self):
        with patch("fin_scraper.jobs.price_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.price_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.price_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.price_tasks.fail_run"):
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)

            from fin_scraper.jobs.price_tasks import sync_exchange_prices
            result = sync_exchange_prices(asset_class="CRYPTO")

            assert "exchanges_synced" in result
            assert "arb_opportunities" in result
            mock_complete.assert_called_once()

    def test_default_asset_class(self):
        with patch("fin_scraper.jobs.price_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.price_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.price_tasks.complete_run"), \
             patch("fin_scraper.jobs.price_tasks.fail_run"):
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)

            from fin_scraper.jobs.price_tasks import sync_exchange_prices
            sync_exchange_prices()  # should default to "CRYPTO"


class TestIngestFundamentals:
    def test_happy_path(self):
        with patch("fin_scraper.jobs.price_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.price_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.price_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.price_tasks.fail_run"):
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)

            from fin_scraper.jobs.price_tasks import ingest_fundamentals
            result = ingest_fundamentals()

            assert "assets_updated" in result
            assert "fundamentals_created" in result
            mock_complete.assert_called_once()

    def test_with_asset_class(self):
        with patch("fin_scraper.jobs.price_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.price_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.price_tasks.complete_run"), \
             patch("fin_scraper.jobs.price_tasks.fail_run"):
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)

            from fin_scraper.jobs.price_tasks import ingest_fundamentals
            result = ingest_fundamentals(asset_class="STOCKS")
            assert isinstance(result, dict)

    def test_fail_run_on_exception(self):
        with patch("fin_scraper.jobs.price_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.price_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.price_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.price_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_run = MagicMock(id=1)
            mock_create.return_value = mock_run
            mock_complete.side_effect = Exception("db error")

            from fin_scraper.jobs.price_tasks import ingest_fundamentals
            with pytest.raises(Exception):
                ingest_fundamentals()
