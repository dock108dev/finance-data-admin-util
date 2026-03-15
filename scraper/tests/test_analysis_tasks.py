"""Tests for market analysis generation tasks."""

from unittest.mock import MagicMock, patch

import pytest


class TestGenerateDailyAnalyses:
    def _run_with_mocks(self):
        with patch("fin_scraper.jobs.analysis_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.analysis_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.analysis_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.analysis_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)

            from fin_scraper.jobs.analysis_tasks import generate_daily_analyses
            result = generate_daily_analyses()
            return result, mock_create, mock_complete, mock_fail, mock_db

    def test_happy_path(self):
        result, _, mock_complete, _, _ = self._run_with_mocks()
        assert "sessions_analyzed" in result
        assert "analyses_created" in result
        mock_complete.assert_called_once()

    def test_create_run_correct_type(self):
        _, mock_create, _, _, mock_db = self._run_with_mocks()
        mock_create.assert_called_once_with(mock_db, "analysis_generation", requested_by="celery_beat")

    def test_fail_run_on_exception(self):
        with patch("fin_scraper.jobs.analysis_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.analysis_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.analysis_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.analysis_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)
            mock_complete.side_effect = Exception("boom")

            from fin_scraper.jobs.analysis_tasks import generate_daily_analyses
            with pytest.raises(Exception):
                generate_daily_analyses()


class TestGenerateAssetAnalysis:
    def _run_with_mocks(self, **kwargs):
        with patch("fin_scraper.jobs.analysis_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.analysis_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.analysis_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.analysis_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)

            from fin_scraper.jobs.analysis_tasks import generate_asset_analysis
            result = generate_asset_analysis(**kwargs)
            return result, mock_create, mock_complete, mock_fail, mock_db

    def test_happy_path(self):
        result, _, mock_complete, _, _ = self._run_with_mocks(
            asset_id=1, session_date="2024-01-15"
        )
        assert result["asset_id"] == 1
        assert result["session_date"] == "2024-01-15"
        mock_complete.assert_called_once()

    def test_create_run_manual_trigger(self):
        _, mock_create, _, _, mock_db = self._run_with_mocks(
            asset_id=1, session_date="2024-01-15"
        )
        mock_create.assert_called_once_with(mock_db, "analysis_generation", requested_by="admin_manual")

    def test_fail_run_on_exception(self):
        with patch("fin_scraper.jobs.analysis_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.analysis_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.analysis_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.analysis_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)
            mock_complete.side_effect = Exception("boom")

            from fin_scraper.jobs.analysis_tasks import generate_asset_analysis
            with pytest.raises(Exception):
                generate_asset_analysis(asset_id=1, session_date="2024-01-15")
