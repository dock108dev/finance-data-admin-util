"""Tests for run execution tracking (run_manager)."""

from unittest.mock import MagicMock, patch

import pytest

from fin_scraper.services.run_manager import (
    RunRecord,
    complete_run,
    create_run,
    fail_run,
)


class TestRunRecord:
    def test_construction(self):
        r = RunRecord(id=1, scraper_type="price_ingest")
        assert r.id == 1
        assert r.scraper_type == "price_ingest"


class TestCreateRun:
    def test_returns_run_record(self):
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (42,)
        mock_db.execute.return_value = mock_result
        run = create_run(mock_db, "price_ingest")
        assert isinstance(run, RunRecord)
        assert run.id == 42
        assert run.scraper_type == "price_ingest"

    def test_commits_after_insert(self):
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        mock_db.execute.return_value = mock_result
        create_run(mock_db, "price_ingest")
        mock_db.commit.assert_called_once()

    def test_custom_requested_by(self):
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        mock_db.execute.return_value = mock_result
        create_run(mock_db, "price_ingest", requested_by="admin_manual")
        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params["requested_by"] == "admin_manual"

    def test_returns_dummy_on_exception(self):
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("DB error")
        run = create_run(mock_db, "price_ingest")
        assert run.id == -1
        assert run.scraper_type == "price_ingest"


class TestCompleteRun:
    def test_executes_update(self):
        mock_db = MagicMock()
        run = RunRecord(id=10, scraper_type="test")
        complete_run(mock_db, run, summary="done")
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_noop_for_dummy_run(self):
        mock_db = MagicMock()
        run = RunRecord(id=-1, scraper_type="test")
        complete_run(mock_db, run)
        mock_db.execute.assert_not_called()

    def test_graceful_on_exception(self):
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("DB error")
        run = RunRecord(id=10, scraper_type="test")
        # Should not raise
        complete_run(mock_db, run, summary="done")


class TestFailRun:
    def test_executes_update(self):
        mock_db = MagicMock()
        run = RunRecord(id=10, scraper_type="test")
        fail_run(mock_db, run, error="boom")
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_noop_for_dummy_run(self):
        mock_db = MagicMock()
        run = RunRecord(id=-1, scraper_type="test")
        fail_run(mock_db, run, error="boom")
        mock_db.execute.assert_not_called()

    def test_graceful_on_exception(self):
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("DB error")
        run = RunRecord(id=10, scraper_type="test")
        # Should not raise
        fail_run(mock_db, run, error="boom")
