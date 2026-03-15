"""Shared fixtures for scraper tests — mocks only, no real DB or Celery."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_db_session():
    """Sync MagicMock that behaves like a SQLAlchemy Session."""
    session = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    session.execute = MagicMock()
    return session


@pytest.fixture
def mock_get_db_session(mock_db_session):
    """Patch get_db_session to yield mock_db_session."""
    with patch("fin_scraper.db.get_db_session") as mock_ctx:
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db_session)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_ctx


@pytest.fixture
def mock_run_manager():
    """Patch run_manager functions: create_run, complete_run, fail_run."""
    run = MagicMock()
    run.id = 42
    run.scraper_type = "test"

    with patch("fin_scraper.services.run_manager.create_run", return_value=run) as m_create, \
         patch("fin_scraper.services.run_manager.complete_run") as m_complete, \
         patch("fin_scraper.services.run_manager.fail_run") as m_fail:
        yield {
            "create_run": m_create,
            "complete_run": m_complete,
            "fail_run": m_fail,
            "run": run,
        }
