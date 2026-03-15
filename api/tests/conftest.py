"""Shared fixtures for API tests — mocks only, no real DB or HTTP."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings


@pytest.fixture
def mock_settings():
    """Settings with test defaults."""
    return Settings(
        environment="test",
        database_url="postgresql+asyncpg://test:test@localhost/testdb",
        api_key="test-api-key",
        debug=True,
    )


@pytest.fixture
def mock_db_session():
    """AsyncMock that behaves like an AsyncSession."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def auth_headers():
    """Valid auth headers for test requests."""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def client(mock_db_session, mock_settings):
    """httpx AsyncClient wired to the FastAPI app with mocked deps."""
    from app.config import get_settings
    from app.db.session import get_db
    from main import create_app

    # Clear cached settings
    get_settings.cache_clear()

    app = create_app()

    async def _override_get_db():
        yield mock_db_session

    def _override_get_settings():
        return mock_settings

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_settings] = _override_get_settings

    # Mock Celery client so admin endpoints don't need Redis
    mock_celery = MagicMock()
    mock_result = MagicMock()
    mock_result.id = "test-task-id-123"
    mock_celery.send_task.return_value = mock_result

    with patch("app.routers.admin.get_celery_app", return_value=mock_celery):
        transport = ASGITransport(app=app)
        yield AsyncClient(transport=transport, base_url="http://test")
