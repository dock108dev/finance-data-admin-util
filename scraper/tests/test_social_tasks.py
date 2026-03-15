"""Tests for social and news ingestion tasks."""

from unittest.mock import MagicMock, patch

import pytest


class TestCollectSocialSentiment:
    def _run_with_mocks(self, **kwargs):
        with patch("fin_scraper.jobs.social_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.social_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.social_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.social_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)

            from fin_scraper.jobs.social_tasks import collect_social_sentiment
            result = collect_social_sentiment(**kwargs)
            return result, mock_create, mock_complete, mock_fail, mock_db

    def test_happy_path(self):
        result, _, mock_complete, _, _ = self._run_with_mocks()
        assert "twitter_posts_collected" in result
        assert "reddit_posts_collected" in result
        mock_complete.assert_called_once()

    def test_create_run_correct_type(self):
        _, mock_create, _, _, mock_db = self._run_with_mocks()
        mock_create.assert_called_once_with(mock_db, "social_collect", requested_by="celery_beat")

    def test_with_asset_class(self):
        result, _, _, _, _ = self._run_with_mocks(asset_class="CRYPTO")
        assert isinstance(result, dict)

    def test_with_hours_back(self):
        result, _, _, _, _ = self._run_with_mocks(hours_back=6)
        assert isinstance(result, dict)

    def test_fail_run_on_exception(self):
        with patch("fin_scraper.jobs.social_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.social_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.social_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.social_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)
            mock_complete.side_effect = Exception("boom")

            from fin_scraper.jobs.social_tasks import collect_social_sentiment
            with pytest.raises(Exception):
                collect_social_sentiment()


class TestIngestNews:
    def _run_with_mocks(self, **kwargs):
        with patch("fin_scraper.jobs.social_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.social_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.social_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.social_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)

            from fin_scraper.jobs.social_tasks import ingest_news
            result = ingest_news(**kwargs)
            return result, mock_create, mock_complete, mock_fail, mock_db

    def test_happy_path(self):
        result, _, mock_complete, _, _ = self._run_with_mocks()
        assert "articles_fetched" in result
        assert "articles_created" in result
        mock_complete.assert_called_once()

    def test_create_run_correct_type(self):
        _, mock_create, _, _, mock_db = self._run_with_mocks()
        mock_create.assert_called_once_with(mock_db, "news_ingest", requested_by="celery_beat")

    def test_fail_run_on_exception(self):
        with patch("fin_scraper.jobs.social_tasks.get_db_session") as mock_ctx, \
             patch("fin_scraper.jobs.social_tasks.create_run") as mock_create, \
             patch("fin_scraper.jobs.social_tasks.complete_run") as mock_complete, \
             patch("fin_scraper.jobs.social_tasks.fail_run") as mock_fail:
            mock_db = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_create.return_value = MagicMock(id=1)
            mock_complete.side_effect = Exception("boom")

            from fin_scraper.jobs.social_tasks import ingest_news
            with pytest.raises(Exception):
                ingest_news()
