"""Tests for stock data scraper."""

from unittest.mock import MagicMock, patch

import pytest

from fin_scraper.scrapers.stocks import StockScraper


class TestStockScraperInit:
    def test_stores_db_session(self):
        mock_db = MagicMock()
        scraper = StockScraper(mock_db)
        assert scraper.db is mock_db


class TestIngestDaily:
    def test_with_explicit_tickers(self):
        mock_db = MagicMock()
        scraper = StockScraper(mock_db)
        with patch.object(scraper, "_fetch_daily_candles", return_value=[]) as mock_fetch, \
             patch.object(scraper, "_persist_candles") as mock_persist, \
             patch.object(scraper, "_update_session") as mock_update:
            result = scraper.ingest_daily(tickers=["AAPL", "MSFT"])
            assert result["processed"] == 2
            assert mock_fetch.call_count == 2

    def test_with_none_tickers_queries_db(self):
        mock_db = MagicMock()
        scraper = StockScraper(mock_db)
        with patch.object(scraper, "_get_active_tickers", return_value=["TSLA"]) as mock_get, \
             patch.object(scraper, "_fetch_daily_candles", return_value=[]), \
             patch.object(scraper, "_persist_candles"), \
             patch.object(scraper, "_update_session"):
            result = scraper.ingest_daily()
            mock_get.assert_called_once()
            assert result["processed"] == 1

    def test_error_resilience_per_ticker(self):
        mock_db = MagicMock()
        scraper = StockScraper(mock_db)
        with patch.object(scraper, "_fetch_daily_candles", side_effect=[Exception("fail"), []]), \
             patch.object(scraper, "_persist_candles"), \
             patch.object(scraper, "_update_session"):
            result = scraper.ingest_daily(tickers=["BAD", "GOOD"])
            assert result["errors"] == 1
            assert result["processed"] == 1

    def test_counts_created_candles(self):
        mock_db = MagicMock()
        scraper = StockScraper(mock_db)
        candles = [{"o": 1}, {"o": 2}, {"o": 3}]
        with patch.object(scraper, "_fetch_daily_candles", return_value=candles), \
             patch.object(scraper, "_persist_candles"), \
             patch.object(scraper, "_update_session"):
            result = scraper.ingest_daily(tickers=["AAPL"])
            assert result["created"] == 3


class TestIngestIntraday:
    def test_happy_path(self):
        mock_db = MagicMock()
        scraper = StockScraper(mock_db)
        with patch.object(scraper, "_fetch_intraday_candles", return_value=[]) as mock_fetch, \
             patch.object(scraper, "_persist_candles"):
            result = scraper.ingest_intraday(tickers=["AAPL"])
            assert result["processed"] == 1
            mock_fetch.assert_called_once_with("AAPL", "5m")

    def test_custom_interval(self):
        mock_db = MagicMock()
        scraper = StockScraper(mock_db)
        with patch.object(scraper, "_fetch_intraday_candles", return_value=[]) as mock_fetch, \
             patch.object(scraper, "_persist_candles"):
            scraper.ingest_intraday(tickers=["AAPL"], interval="15m")
            mock_fetch.assert_called_once_with("AAPL", "15m")

    def test_error_resilience(self):
        mock_db = MagicMock()
        scraper = StockScraper(mock_db)
        with patch.object(scraper, "_fetch_intraday_candles", side_effect=Exception("fail")), \
             patch.object(scraper, "_persist_candles"):
            result = scraper.ingest_intraday(tickers=["BAD"])
            assert result["processed"] == 0


class TestFetchFundamentals:
    def test_returns_dict(self):
        mock_db = MagicMock()
        scraper = StockScraper(mock_db)
        result = scraper.fetch_fundamentals("AAPL")
        assert isinstance(result, dict)


class TestPrivateMethods:
    def test_get_active_tickers_returns_list(self):
        mock_db = MagicMock()
        scraper = StockScraper(mock_db)
        result = scraper._get_active_tickers()
        assert isinstance(result, list)
