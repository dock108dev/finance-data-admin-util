"""Tests for application configuration (Settings + get_settings)."""

import os
from unittest.mock import patch

import pytest

from app.config import Settings, get_settings


class TestSettingsDefaults:
    def test_default_environment(self):
        s = Settings()
        assert s.environment == "development"

    def test_default_log_level(self):
        s = Settings()
        assert s.log_level == "INFO"

    def test_default_debug_false(self):
        s = Settings()
        assert s.debug is False

    def test_default_database_url(self):
        s = Settings()
        assert "asyncpg" in s.database_url

    def test_default_api_key(self):
        s = Settings()
        assert s.api_key == "dev-key-do-not-use-in-production"

    def test_default_rate_limit(self):
        s = Settings()
        assert s.rate_limit_requests == 120
        assert s.rate_limit_window_seconds == 60


class TestSettingsOverrides:
    def test_env_var_overrides_environment(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            s = Settings()
            assert s.environment == "production"

    def test_env_var_overrides_api_key(self):
        with patch.dict(os.environ, {"API_KEY": "my-secret-key"}):
            s = Settings()
            assert s.api_key == "my-secret-key"


class TestGetSettings:
    def test_returns_settings_instance(self):
        get_settings.cache_clear()
        result = get_settings()
        assert isinstance(result, Settings)

    def test_caching(self):
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_cache_clear(self):
        get_settings.cache_clear()
        s1 = get_settings()
        get_settings.cache_clear()
        s2 = get_settings()
        assert s1 is not s2
