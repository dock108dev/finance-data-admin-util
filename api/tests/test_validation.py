"""Tests for validation utilities."""

import pytest
from datetime import datetime, timezone

from app.utils.validation import (
    validate_ticker,
    validate_interval,
    validate_price,
    is_market_hours,
)


class TestValidateTicker:
    def test_normalizes_to_uppercase(self):
        assert validate_ticker("aapl") == "AAPL"

    def test_strips_whitespace(self):
        assert validate_ticker("  BTC  ") == "BTC"

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            validate_ticker("")

    def test_rejects_too_long(self):
        with pytest.raises(ValueError):
            validate_ticker("A" * 25)


class TestValidateInterval:
    def test_accepts_valid_intervals(self):
        for interval in ["1m", "5m", "15m", "1h", "1d"]:
            assert validate_interval(interval) == interval

    def test_rejects_invalid(self):
        with pytest.raises(ValueError):
            validate_interval("2m")


class TestValidatePrice:
    def test_accepts_positive(self):
        assert validate_price(100.0) == 100.0

    def test_rejects_zero(self):
        with pytest.raises(ValueError):
            validate_price(0.0)

    def test_rejects_negative(self):
        with pytest.raises(ValueError):
            validate_price(-10.0)


class TestIsMarketHours:
    def test_crypto_always_open(self):
        any_time = datetime(2024, 1, 15, 3, 0, tzinfo=timezone.utc)
        assert is_market_hours(any_time, "CRYPTO") is True

    def test_stocks_closed_on_weekend(self):
        saturday = datetime(2024, 1, 13, 16, 0, tzinfo=timezone.utc)
        assert is_market_hours(saturday, "STOCKS") is False

    def test_stocks_open_during_hours(self):
        # 3:00 PM UTC = 10:00 AM ET (market hours)
        market_time = datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)
        assert is_market_hours(market_time, "STOCKS") is True

    def test_stocks_closed_after_hours(self):
        # 10:00 PM UTC = 5:00 PM ET (after close)
        after_hours = datetime(2024, 1, 15, 22, 0, tzinfo=timezone.utc)
        assert is_market_hours(after_hours, "STOCKS") is False
