"""Tests for the data normalization module."""

import sys
import os
from datetime import datetime, timezone

# Add scraper to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scraper"))

from fin_scraper.normalization import (
    normalize_price,
    normalize_volume,
    normalize_timestamp,
    normalize_ticker,
    normalize_candle,
)


class TestNormalizePrice:
    def test_float_passthrough(self):
        assert normalize_price(100.5) == 100.5

    def test_string_to_float(self):
        assert normalize_price("99.99") == 99.99

    def test_none(self):
        assert normalize_price(None) is None

    def test_invalid_string(self):
        assert normalize_price("not_a_number") is None


class TestNormalizeVolume:
    def test_float_passthrough(self):
        assert normalize_volume(1000.0) == 1000.0

    def test_k_suffix(self):
        assert normalize_volume("1.5K") == 1500.0

    def test_m_suffix(self):
        assert normalize_volume("2.5M") == 2500000.0

    def test_b_suffix(self):
        assert normalize_volume("1B") == 1000000000.0

    def test_comma_separated(self):
        assert normalize_volume("1,234,567") == 1234567.0

    def test_none(self):
        assert normalize_volume(None) is None

    def test_invalid(self):
        assert normalize_volume("abc") is None


class TestNormalizeTimestamp:
    def test_datetime_passthrough(self):
        dt = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        assert normalize_timestamp(dt) == dt

    def test_naive_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30)
        result = normalize_timestamp(dt)
        assert result.tzinfo == timezone.utc

    def test_unix_seconds(self):
        ts = 1705312200  # 2024-01-15 10:30 UTC
        result = normalize_timestamp(ts)
        assert result is not None
        assert result.year == 2024

    def test_unix_milliseconds(self):
        ts = 1705312200000
        result = normalize_timestamp(ts)
        assert result is not None
        assert result.year == 2024

    def test_iso_string(self):
        result = normalize_timestamp("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2024

    def test_date_string(self):
        result = normalize_timestamp("2024-01-15")
        assert result is not None
        assert result.year == 2024

    def test_none(self):
        assert normalize_timestamp(None) is None

    def test_invalid_string(self):
        assert normalize_timestamp("not a date") is None


class TestNormalizeTicker:
    def test_basic(self):
        assert normalize_ticker("AAPL") == "AAPL"

    def test_lowercase(self):
        assert normalize_ticker("btc") == "BTC"

    def test_strip_usdt(self):
        assert normalize_ticker("BTCUSDT") == "BTC"

    def test_strip_usd_suffix(self):
        assert normalize_ticker("BTC-USD") == "BTC"

    def test_strip_whitespace(self):
        assert normalize_ticker("  ETH  ") == "ETH"


class TestNormalizeCandle:
    def test_standard_format(self):
        raw = {"timestamp": "2024-01-15T10:00:00Z", "open": 100, "high": 105,
               "low": 98, "close": 103, "volume": "1M"}
        result = normalize_candle(raw, "test")
        assert result["open"] == 100
        assert result["high"] == 105
        assert result["volume"] == 1000000
        assert result["source"] == "test"

    def test_short_keys(self):
        raw = {"t": "2024-01-15", "o": 100, "h": 105, "l": 98, "c": 103, "v": 5000}
        result = normalize_candle(raw, "binance")
        assert result["open"] == 100
        assert result["close"] == 103
