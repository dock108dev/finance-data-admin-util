"""Tests for exchange price synchronizer."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from fin_scraper.prices.synchronizer import (
    ExchangePriceSynchronizer,
    NormalizedPrice,
)


class TestNormalizedPrice:
    def test_construction(self):
        p = NormalizedPrice(
            asset_ticker="BTC",
            exchange="Binance",
            price=65000.0,
            bid=64990.0,
            ask=65010.0,
        )
        assert p.asset_ticker == "BTC"
        assert p.exchange == "Binance"
        assert p.price == 65000.0

    def test_defaults(self):
        p = NormalizedPrice(asset_ticker="ETH", exchange="Coinbase", price=3500.0)
        assert p.bid is None
        assert p.ask is None
        assert p.volume_24h is None
        assert p.observed_at is None


class TestExchangePriceSynchronizer:
    def test_init(self):
        mock_db = MagicMock()
        sync = ExchangePriceSynchronizer(mock_db, asset_class="CRYPTO")
        assert sync.db is mock_db
        assert sync.asset_class == "CRYPTO"

    def test_default_asset_class(self):
        mock_db = MagicMock()
        sync = ExchangePriceSynchronizer(mock_db)
        assert sync.asset_class == "CRYPTO"


class TestSyncAll:
    def test_empty_exchanges(self):
        mock_db = MagicMock()
        sync = ExchangePriceSynchronizer(mock_db)
        with patch.object(sync, "_get_exchange_clients", return_value={}):
            result = sync.sync_all()
            assert result["exchanges_synced"] == 0
            assert result["errors"] == 0

    def test_syncs_exchange(self):
        mock_db = MagicMock()
        sync = ExchangePriceSynchronizer(mock_db)
        mock_client = MagicMock()
        mock_client.fetch_all_prices.return_value = [
            {"symbol": "BTC", "price": 65000, "bid": None, "ask": None, "volume": None}
        ]
        with patch.object(sync, "_get_exchange_clients",
                         return_value={"Binance": mock_client}), \
             patch.object(sync, "_upsert_exchange_prices"), \
             patch.object(sync, "_upsert_arb_work"):
            result = sync.sync_all()
            assert result["exchanges_synced"] == 1
            assert result["prices_upserted"] == 1

    def test_error_per_exchange(self):
        mock_db = MagicMock()
        sync = ExchangePriceSynchronizer(mock_db)
        mock_client = MagicMock()
        mock_client.fetch_all_prices.side_effect = Exception("API error")
        with patch.object(sync, "_get_exchange_clients",
                         return_value={"Binance": mock_client}):
            result = sync.sync_all()
            assert result["errors"] == 1
            assert result["exchanges_synced"] == 0

    def test_multiple_exchanges(self):
        mock_db = MagicMock()
        sync = ExchangePriceSynchronizer(mock_db)
        client_a = MagicMock()
        client_a.fetch_all_prices.return_value = [{"symbol": "BTC", "price": 65000}]
        client_b = MagicMock()
        client_b.fetch_all_prices.return_value = [{"symbol": "BTC", "price": 65100}]
        with patch.object(sync, "_get_exchange_clients",
                         return_value={"Binance": client_a, "Coinbase": client_b}), \
             patch.object(sync, "_upsert_exchange_prices"), \
             patch.object(sync, "_upsert_arb_work"):
            result = sync.sync_all()
            assert result["exchanges_synced"] == 2


class TestNormalize:
    def test_normalizes_raw_price(self):
        mock_db = MagicMock()
        sync = ExchangePriceSynchronizer(mock_db)
        raw = {"symbol": "ETH", "price": "3500.50", "bid": 3500, "ask": 3501, "volume": 1e6}
        result = sync._normalize(raw, "Kraken")
        assert isinstance(result, NormalizedPrice)
        assert result.exchange == "Kraken"
        assert result.price == 3500.50
        assert result.bid == 3500

    def test_handles_missing_fields(self):
        mock_db = MagicMock()
        sync = ExchangePriceSynchronizer(mock_db)
        raw = {"symbol": "SOL", "price": "150"}
        result = sync._normalize(raw, "Binance")
        assert result.bid is None
        assert result.ask is None

    def test_sets_observed_at(self):
        mock_db = MagicMock()
        sync = ExchangePriceSynchronizer(mock_db)
        raw = {"symbol": "BTC", "price": "65000"}
        result = sync._normalize(raw, "Binance")
        assert result.observed_at is not None
