"""Tests for async DB session management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db import session as session_mod


class TestInitDb:
    @pytest.mark.asyncio
    async def test_creates_engine(self):
        session_mod._engine = None
        session_mod._session_factory = None
        with patch("app.db.session.create_async_engine") as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine
            await session_mod.init_db("postgresql+asyncpg://x/y")
            mock_create.assert_called_once()
            assert session_mod._engine is mock_engine

    @pytest.mark.asyncio
    async def test_creates_session_factory(self):
        session_mod._engine = None
        session_mod._session_factory = None
        with patch("app.db.session.create_async_engine") as mock_create, \
             patch("app.db.session.async_sessionmaker") as mock_maker:
            mock_create.return_value = MagicMock()
            await session_mod.init_db("postgresql+asyncpg://x/y")
            mock_maker.assert_called_once()
            assert session_mod._session_factory is not None


class TestGetDb:
    @pytest.mark.asyncio
    async def test_raises_if_not_initialized(self):
        session_mod._session_factory = None
        with pytest.raises(RuntimeError, match="Database not initialized"):
            async for _ in session_mod.get_db():
                pass

    @pytest.mark.asyncio
    async def test_yields_session(self):
        mock_session = AsyncMock()
        mock_factory = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_ctx.__aexit__.return_value = False
        mock_factory.return_value = mock_ctx
        session_mod._session_factory = mock_factory

        gen = session_mod.get_db()
        sess = await gen.__anext__()
        assert sess is mock_session

    @pytest.mark.asyncio
    async def test_commits_on_success(self):
        mock_session = AsyncMock()
        mock_factory = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_ctx.__aexit__.return_value = False
        mock_factory.return_value = mock_ctx
        session_mod._session_factory = mock_factory

        gen = session_mod.get_db()
        await gen.__anext__()
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rollback_on_exception(self):
        mock_session = AsyncMock()
        mock_factory = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_ctx.__aexit__.return_value = False
        mock_factory.return_value = mock_ctx
        session_mod._session_factory = mock_factory

        gen = session_mod.get_db()
        await gen.__anext__()
        with pytest.raises(ValueError):
            await gen.athrow(ValueError("test"))
        mock_session.rollback.assert_awaited_once()
