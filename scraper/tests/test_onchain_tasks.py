"""Tests for on-chain data sync tasks."""

from unittest.mock import MagicMock, patch

import pytest


class TestSyncOnchainData:
    def _run_with_mocks(self, **kwargs):
        with patch("fin_scraper.jobs.onchain_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.onchain_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.onchain_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.onchain_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)

            from fin_scraper.jobs.onchain_tasks import sync_onchain_data
            result = sync_onchain_data(**kwargs)
            return result, mock_create, mock_complete, mock_fail, mock_db

    def test_happy_path(self):
        result, _, mock_complete, _, _ = self._run_with_mocks()
        assert "whale_transactions" in result
        assert "metrics_updated" in result
        mock_complete.assert_called_once()

    def test_create_run_correct_type(self):
        _, mock_create, _, _, mock_db = self._run_with_mocks()
        mock_create.assert_called_once_with(mock_db, "onchain_sync", requested_by="celery_beat")

    def test_custom_chain(self):
        result, _, _, _, _ = self._run_with_mocks(chain="bitcoin")
        assert isinstance(result, dict)

    def test_fail_run_on_exception(self):
        with patch("fin_scraper.jobs.onchain_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.onchain_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.onchain_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.onchain_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)
            mock_complete.side_effect = Exception("boom")

            from fin_scraper.jobs.onchain_tasks import sync_onchain_data
            with pytest.raises(Exception):
                sync_onchain_data()
