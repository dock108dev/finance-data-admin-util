"""Tests for crypto data scraper."""

from unittest.mock import MagicMock, patch

import pytest

from fin_scraper.scrapers.crypto import CryptoScraper


class TestCryptoScraperInit:
    def test_stores_db_session(self):
        mock_db = MagicMock()
        scraper = CryptoScraper(mock_db)
        assert scraper.db is mock_db


class TestIngestDaily:
    def test_with_explicit_tokens(self):
        mock_db = MagicMock()
        scraper = CryptoScraper(mock_db)
        with patch.object(scraper, "_fetch_daily_from_coingecko", return_value=[]) as mock_fetch, \
             patch.object(scraper, "_persist_candles"):
            result = scraper.ingest_daily(tokens=["BTC", "ETH"])
            assert result["processed"] == 2
            assert mock_fetch.call_count == 2

    def test_with_none_tokens_queries_db(self):
        mock_db = MagicMock()
        scraper = CryptoScraper(mock_db)
        with patch.object(scraper, "_get_active_tokens", return_value=["SOL"]) as mock_get, \
             patch.object(scraper, "_fetch_daily_from_coingecko", return_value=[]), \
             patch.object(scraper, "_persist_candles"):
            result = scraper.ingest_daily()
            mock_get.assert_called_once()
            assert result["processed"] == 1

    def test_error_resilience_per_token(self):
        mock_db = MagicMock()
        scraper = CryptoScraper(mock_db)
        with patch.object(scraper, "_fetch_daily_from_coingecko",
                         side_effect=[Exception("fail"), []]), \
             patch.object(scraper, "_persist_candles"):
            result = scraper.ingest_daily(tokens=["BAD", "GOOD"])
            assert result["errors"] == 1
            assert result["processed"] == 1

    def test_counts_created_candles(self):
        mock_db = MagicMock()
        scraper = CryptoScraper(mock_db)
        candles = [{"o": 1}, {"o": 2}]
        with patch.object(scraper, "_fetch_daily_from_coingecko", return_value=candles), \
             patch.object(scraper, "_persist_candles"):
            result = scraper.ingest_daily(tokens=["BTC"])
            assert result["created"] == 2


class TestIngestIntraday:
    def test_happy_path(self):
        mock_db = MagicMock()
        scraper = CryptoScraper(mock_db)
        with patch.object(scraper, "_fetch_binance_klines", return_value=[]) as mock_fetch, \
             patch.object(scraper, "_persist_candles"):
            result = scraper.ingest_intraday(tokens=["BTC"])
            assert result["processed"] == 1
            mock_fetch.assert_called_once_with("BTC", "1m")

    def test_custom_interval(self):
        mock_db = MagicMock()
        scraper = CryptoScraper(mock_db)
        with patch.object(scraper, "_fetch_binance_klines", return_value=[]) as mock_fetch, \
             patch.object(scraper, "_persist_candles"):
            scraper.ingest_intraday(tokens=["BTC"], interval="5m")
            mock_fetch.assert_called_once_with("BTC", "5m")

    def test_error_resilience(self):
        mock_db = MagicMock()
        scraper = CryptoScraper(mock_db)
        with patch.object(scraper, "_fetch_binance_klines", side_effect=Exception("fail")), \
             patch.object(scraper, "_persist_candles"):
            result = scraper.ingest_intraday(tokens=["BAD"])
            assert result["processed"] == 0


class TestFetchExchangePrices:
    def test_returns_list(self):
        mock_db = MagicMock()
        scraper = CryptoScraper(mock_db)
        result = scraper.fetch_exchange_prices("BTC")
        assert isinstance(result, list)


class TestFetchFundamentals:
    def test_returns_dict(self):
        mock_db = MagicMock()
        scraper = CryptoScraper(mock_db)
        result = scraper.fetch_fundamentals("BTC")
        assert isinstance(result, dict)


class TestPrivateMethods:
    def test_get_active_tokens_returns_list(self):
        mock_db = MagicMock()
        scraper = CryptoScraper(mock_db)
        result = scraper._get_active_tokens()
        assert isinstance(result, list)
