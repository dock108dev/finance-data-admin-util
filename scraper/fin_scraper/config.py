"""Centralized configuration — Pydantic Settings loading all API keys + rate limits."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class ScraperSettings(BaseSettings):
    """All scraper configuration, loaded from environment."""

    # Database
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/findata"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── API Keys ──────────────────────────────────────────────────────────
    finnhub_api_key: str = ""
    fred_api_key: str = ""
    binance_api_key: str = ""
    binance_secret_key: str = ""
    coingecko_api_key: str = ""  # Demo key for CoinGecko
    coinmarketcap_api_key: str = ""
    etherscan_api_key: str = ""

    # Social
    x_auth_token: str = ""
    x_ct0: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "fin-data-admin/1.0"

    # ── Rate Limits (calls_per_window / window_seconds) ───────────────────
    finnhub_rate_limit: int = 60
    finnhub_rate_window: int = 60

    coingecko_rate_limit: int = 30
    coingecko_rate_window: int = 60

    binance_rate_limit: int = 1200
    binance_rate_window: int = 60

    etherscan_rate_limit: int = 5
    etherscan_rate_window: int = 1

    fred_rate_limit: int = 120
    fred_rate_window: int = 60

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> ScraperSettings:
    """Cached settings singleton."""
    return ScraperSettings()
