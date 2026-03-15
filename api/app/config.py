"""Application configuration via Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment-driven application settings."""

    # General
    environment: str = "development"
    log_level: str = "INFO"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/findata"

    # Redis
    redis_url: str = "redis://localhost:6379/2"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # API auth
    api_key: str = "dev-key-do-not-use-in-production"

    # CORS
    allowed_cors_origins: list[str] = ["http://localhost:3000"]

    # Rate limiting
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    # JWT Auth
    jwt_secret: str = "dev-jwt-secret-change-in-production"

    # OpenAI
    openai_api_key: str = ""
    openai_model_analysis: str = "gpt-4o"
    openai_model_classification: str = "gpt-4o-mini"

    # Data source keys
    alpha_vantage_api_key: str = ""
    polygon_api_key: str = ""
    binance_api_key: str = ""
    binance_secret_key: str = ""
    coingecko_api_key: str = ""
    etherscan_api_key: str = ""
    news_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
