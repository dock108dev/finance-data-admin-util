"""Tests for signal detection tasks."""

from unittest.mock import MagicMock, patch

import pytest


class TestRunSignalPipeline:
    def _run_with_mocks(self, **kwargs):
        with patch("fin_scraper.jobs.signal_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.signal_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.signal_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.signal_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_run = MagicMock(id=1)
            mock_create.return_value = mock_run

            from fin_scraper.jobs.signal_tasks import run_signal_pipeline
            result = run_signal_pipeline(**kwargs)
            return result, mock_create, mock_complete, mock_fail, mock_db

    def test_happy_path(self):
        result, _, mock_complete, _, _ = self._run_with_mocks()
        assert "assets_scanned" in result
        assert "signals_created" in result
        mock_complete.assert_called_once()

    def test_create_run_correct_type(self):
        _, mock_create, _, _, mock_db = self._run_with_mocks()
        mock_create.assert_called_once_with(mock_db, "signal_pipeline", requested_by="celery_beat")

    def test_with_asset_class_filter(self):
        result, _, _, _, _ = self._run_with_mocks(asset_class="CRYPTO")
        assert isinstance(result, dict)

    def test_with_asset_id_filter(self):
        result, _, _, _, _ = self._run_with_mocks(asset_id=42)
        assert isinstance(result, dict)

    def test_fail_run_on_exception(self):
        with patch("fin_scraper.jobs.signal_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.signal_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.signal_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.signal_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_run = MagicMock(id=1)
            mock_create.return_value = mock_run
            mock_complete.side_effect = Exception("boom")

            from fin_scraper.jobs.signal_tasks import run_signal_pipeline
            with pytest.raises(Exception):
                run_signal_pipeline()
