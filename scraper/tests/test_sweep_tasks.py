"""Tests for daily sweep tasks."""

from unittest.mock import MagicMock, patch

import pytest


class TestRunDailySweep:
    def _run_with_mocks(self):
        with patch("fin_scraper.jobs.sweep_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.sweep_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.sweep_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.sweep_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)

            from fin_scraper.jobs.sweep_tasks import run_daily_sweep
            result = run_daily_sweep()
            return result, mock_create, mock_complete, mock_fail, mock_db

    def test_happy_path(self):
        result, _, mock_complete, _, _ = self._run_with_mocks()
        assert "candles_backfilled" in result
        assert "sessions_closed" in result
        assert "signals_resolved" in result
        mock_complete.assert_called_once()

    def test_create_run_correct_type(self):
        _, mock_create, _, _, mock_db = self._run_with_mocks()
        mock_create.assert_called_once_with(mock_db, "daily_sweep", requested_by="celery_beat")

    def test_returns_all_expected_keys(self):
        result, _, _, _, _ = self._run_with_mocks()
        expected_keys = [
            "candles_backfilled", "sessions_closed", "signals_resolved",
            "arb_entries_pruned", "conflicts_detected", "assets_metadata_updated",
        ]
        for key in expected_keys:
            assert key in result

    def test_fail_run_on_exception(self):
        with patch("fin_scraper.jobs.sweep_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.sweep_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.sweep_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.sweep_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)
            mock_complete.side_effect = Exception("boom")

            from fin_scraper.jobs.sweep_tasks import run_daily_sweep
            with pytest.raises(Exception):
                run_daily_sweep()
