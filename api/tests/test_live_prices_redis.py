"""Tests for the Redis live prices service."""

import json
from unittest.mock import MagicMock, patch

from app.services.live_prices_redis import (
    write_live_price,
    read_live_price,
    read_all_live_prices_for_asset,
    read_price_history,
    discover_live_assets,
)


def _mock_redis():
    """Create a mock Redis client with in-memory storage."""
    storage = {}
    ttls = {}
    lists = {}

    r = MagicMock()

    def setex(key, ttl, value):
        storage[key] = value
        ttls[key] = ttl

    def get(key):
        return storage.get(key)

    def ttl(key):
        return ttls.get(key, -1)

    def lpush(key, value):
        if key not in lists:
            lists[key] = []
        lists[key].insert(0, value)

    def ltrim(key, start, end):
        if key in lists:
            lists[key] = lists[key][start:end + 1]

    def expire(key, ttl):
        ttls[key] = ttl

    def lrange(key, start, end):
        if key not in lists:
            return []
        return lists[key][start:end + 1]

    def scan_iter(match=None, count=None):
        import fnmatch
        if match:
            return [k for k in storage if fnmatch.fnmatch(k, match)]
        return list(storage.keys())

    def ping():
        return True

    r.setex = setex
    r.get = get
    r.ttl = ttl
    r.lpush = lpush
    r.ltrim = ltrim
    r.expire = expire
    r.lrange = lrange
    r.scan_iter = scan_iter
    r.ping = ping

    return r


class TestWriteLivePrice:
    def test_writes_snapshot(self):
        mock_r = _mock_redis()
        with patch("app.services.live_prices_redis._get_redis", return_value=mock_r):
            write_live_price("CRYPTO", 1, "Binance", 50000.0, bid=49999, ask=50001)

        key = "live:price:CRYPTO:1:Binance"
        raw = mock_r.get(key)
        assert raw is not None
        data = json.loads(raw)
        assert data["price"] == 50000.0
        assert data["bid"] == 49999
        assert data["ask"] == 50001
        assert data["exchange"] == "Binance"

    def test_writes_history(self):
        mock_r = _mock_redis()
        with patch("app.services.live_prices_redis._get_redis", return_value=mock_r):
            write_live_price("CRYPTO", 1, "Binance", 50000.0)
            write_live_price("CRYPTO", 1, "Binance", 50100.0)


class TestReadLivePrice:
    def test_reads_existing_snapshot(self):
        mock_r = _mock_redis()
        with patch("app.services.live_prices_redis._get_redis", return_value=mock_r):
            write_live_price("CRYPTO", 1, "Binance", 50000.0)
            result = read_live_price("CRYPTO", 1, "Binance")

        assert result is not None
        assert result["price"] == 50000.0
        assert "ttl_seconds_remaining" in result

    def test_returns_none_for_missing(self):
        mock_r = _mock_redis()
        with patch("app.services.live_prices_redis._get_redis", return_value=mock_r):
            result = read_live_price("CRYPTO", 999, "Unknown")
        assert result is None


class TestReadAllLivePrices:
    def test_reads_multiple_exchanges(self):
        mock_r = _mock_redis()
        with patch("app.services.live_prices_redis._get_redis", return_value=mock_r):
            write_live_price("CRYPTO", 1, "Binance", 50000.0)
            write_live_price("CRYPTO", 1, "Coinbase", 50100.0)
            result = read_all_live_prices_for_asset("CRYPTO", 1)

        assert len(result) == 2
        assert "Binance" in result
        assert "Coinbase" in result
        assert result["Binance"]["price"] == 50000.0
        assert result["Coinbase"]["price"] == 50100.0

    def test_returns_empty_for_no_data(self):
        mock_r = _mock_redis()
        with patch("app.services.live_prices_redis._get_redis", return_value=mock_r):
            result = read_all_live_prices_for_asset("CRYPTO", 999)
        assert result == {}


class TestReadPriceHistory:
    def test_reads_history(self):
        mock_r = _mock_redis()
        with patch("app.services.live_prices_redis._get_redis", return_value=mock_r):
            for i in range(5):
                write_live_price("CRYPTO", 1, "Binance", 50000 + i)
            result = read_price_history(1, "Binance", count=3)

        assert len(result) == 3
        # Most recent first
        assert result[0]["price"] == 50004

    def test_returns_empty_for_no_history(self):
        mock_r = _mock_redis()
        with patch("app.services.live_prices_redis._get_redis", return_value=mock_r):
            result = read_price_history(999, "Unknown")
        assert result == []


class TestDiscoverLiveAssets:
    def test_discovers_assets(self):
        mock_r = _mock_redis()
        with patch("app.services.live_prices_redis._get_redis", return_value=mock_r):
            write_live_price("CRYPTO", 1, "Binance", 50000)
            write_live_price("CRYPTO", 2, "Binance", 3000)
            write_live_price("STOCKS", 10, "NYSE", 150)
            result = discover_live_assets()

        assert len(result) == 3

    def test_filter_by_asset_class(self):
        mock_r = _mock_redis()
        with patch("app.services.live_prices_redis._get_redis", return_value=mock_r):
            write_live_price("CRYPTO", 1, "Binance", 50000)
            write_live_price("STOCKS", 10, "NYSE", 150)
            result = discover_live_assets(asset_class="CRYPTO")

        crypto_assets = [a for a in result if a[0] == "CRYPTO"]
        assert len(crypto_assets) >= 1

    def test_no_duplicates(self):
        mock_r = _mock_redis()
        with patch("app.services.live_prices_redis._get_redis", return_value=mock_r):
            write_live_price("CRYPTO", 1, "Binance", 50000)
            write_live_price("CRYPTO", 1, "Coinbase", 50100)
            result = discover_live_assets()

        asset_ids = [(a, b) for a, b in result]
        assert len(asset_ids) == len(set(asset_ids))
