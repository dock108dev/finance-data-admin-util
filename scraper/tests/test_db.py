"""Tests for scraper sync DB session management."""

from unittest.mock import MagicMock, patch

import pytest

from fin_scraper import db as db_mod


class TestGetEngine:
    def test_creates_engine(self):
        db_mod._engine = None
        with patch("fin_scraper.db.create_engine") as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine
            result = db_mod.get_engine()
            mock_create.assert_called_once()
            assert result is mock_engine

    def test_caches_engine(self):
        db_mod._engine = None
        with patch("fin_scraper.db.create_engine") as mock_create:
            mock_create.return_value = MagicMock()
            e1 = db_mod.get_engine()
            e2 = db_mod.get_engine()
            assert e1 is e2
            mock_create.assert_called_once()

    def test_uses_env_var(self):
        db_mod._engine = None
        with patch("fin_scraper.db.create_engine") as mock_create, \
             patch.dict("os.environ", {"DATABASE_URL_SYNC": "postgresql://custom/db"}):
            mock_create.return_value = MagicMock()
            db_mod.get_engine()
            call_args = mock_create.call_args
            assert call_args[0][0] == "postgresql://custom/db"


class TestGetSessionFactory:
    def test_creates_factory(self):
        db_mod._SessionLocal = None
        db_mod._engine = None
        with patch("fin_scraper.db.create_engine") as mock_create, \
             patch("fin_scraper.db.sessionmaker") as mock_maker:
            mock_create.return_value = MagicMock()
            mock_maker.return_value = MagicMock()
            result = db_mod.get_session_factory()
            mock_maker.assert_called_once()
            assert result is not None

    def test_caches_factory(self):
        db_mod._SessionLocal = None
        db_mod._engine = None
        with patch("fin_scraper.db.create_engine") as mock_create, \
             patch("fin_scraper.db.sessionmaker") as mock_maker:
            mock_create.return_value = MagicMock()
            mock_maker.return_value = MagicMock()
            f1 = db_mod.get_session_factory()
            f2 = db_mod.get_session_factory()
            assert f1 is f2
            mock_maker.assert_called_once()


class TestGetDbSession:
    def test_yields_session(self):
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        db_mod._SessionLocal = mock_factory
        with db_mod.get_db_session() as session:
            assert session is mock_session

    def test_commits_on_success(self):
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        db_mod._SessionLocal = mock_factory
        with db_mod.get_db_session():
            pass
        mock_session.commit.assert_called_once()

    def test_rollback_on_exception(self):
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        db_mod._SessionLocal = mock_factory
        with pytest.raises(ValueError):
            with db_mod.get_db_session():
                raise ValueError("test")
        mock_session.rollback.assert_called_once()

    def test_always_closes(self):
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        db_mod._SessionLocal = mock_factory
        try:
            with db_mod.get_db_session():
                raise ValueError("test")
        except ValueError:
            pass
        mock_session.close.assert_called_once()
