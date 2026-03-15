"""Price ingestion tasks — EOD, intraday, exchange sync, fundamentals.

All tasks use sync SQLAlchemy sessions via get_db_session().
"""

import structlog
from celery import shared_task

from fin_scraper.db import get_db_session
from fin_scraper.services.run_manager import create_run, complete_run, fail_run

logger = structlog.get_logger(__name__)


@shared_task(name="fin_scraper.jobs.price_tasks.ingest_daily_prices")
def ingest_daily_prices() -> dict:
    """Ingest end-of-day OHLCV data for all tracked assets.

    Sources: yfinance (stocks), Binance/CoinGecko (crypto).
    """
    with get_db_session() as db:
        run = create_run(db, "price_ingest", requested_by="celery_beat")
        try:
            logger.info("price_ingest.start")

            from fin_scraper.scrapers.stocks import StockScraper
            from fin_scraper.scrapers.crypto import CryptoScraper

            stock_results = StockScraper(db).ingest_daily()
            crypto_results = CryptoScraper(db).ingest_daily()

            results = {
                "stocks_processed": stock_results.get("processed", 0),
                "crypto_processed": crypto_results.get("processed", 0),
                "candles_created": (
                    stock_results.get("created", 0) + crypto_results.get("created", 0)
                ),
                "errors": (
                    stock_results.get("errors", 0) + crypto_results.get("errors", 0)
                ),
            }

            complete_run(db, run, summary=str(results))
            logger.info("price_ingest.complete", **results)
            return results

        except Exception as e:
            fail_run(db, run, error=str(e))
            logger.error("price_ingest.failed", error=str(e))
            raise


@shared_task(name="fin_scraper.jobs.price_tasks.ingest_intraday_prices")
def ingest_intraday_prices() -> dict:
    """Ingest intraday candles — live price polling.

    Only runs during market hours for stocks; 24/7 for crypto.
    """
    with get_db_session() as db:
        run = create_run(db, "intraday_ingest", requested_by="celery_beat")
        try:
            logger.info("intraday_ingest.start")

            from fin_scraper.utils.market_hours import is_market_open
            from fin_scraper.scrapers.stocks import StockScraper
            from fin_scraper.scrapers.crypto import CryptoScraper

            results = {"candles_created": 0, "assets_polled": 0}

            # Stocks: only during market hours
            if is_market_open():
                stock_results = StockScraper(db).ingest_intraday(interval="5m")
                results["candles_created"] += stock_results.get("created", 0)
                results["assets_polled"] += stock_results.get("processed", 0)
                logger.info("intraday_ingest.stocks_done", **stock_results)

            # Crypto: always runs
            crypto_results = CryptoScraper(db).ingest_intraday(interval="5m")
            results["candles_created"] += crypto_results.get("created", 0)
            results["assets_polled"] += crypto_results.get("processed", 0)

            complete_run(db, run, summary=str(results))
            return results

        except Exception as e:
            fail_run(db, run, error=str(e))
            raise


@shared_task(name="fin_scraper.jobs.price_tasks.sync_exchange_prices")
def sync_exchange_prices(asset_class: str = "CRYPTO") -> dict:
    """Sync cross-exchange prices for arbitrage detection.

    Runs every 1 minute for crypto to capture arb opportunities.
    """
    with get_db_session() as db:
        run = create_run(db, "exchange_sync", requested_by="celery_beat")
        try:
            logger.info("exchange_sync.start", asset_class=asset_class)

            from fin_scraper.prices.synchronizer import ExchangePriceSynchronizer

            sync = ExchangePriceSynchronizer(db, asset_class)
            results = sync.sync_all()

            complete_run(db, run, summary=str(results))
            return results

        except Exception as e:
            fail_run(db, run, error=str(e))
            raise


@shared_task(name="fin_scraper.jobs.price_tasks.ingest_fundamentals")
def ingest_fundamentals(asset_class: str | None = None) -> dict:
    """Ingest fundamental data — P/E, EPS, TVL, supply, etc."""
    with get_db_session() as db:
        run = create_run(db, "fundamental_ingest", requested_by="celery_beat")
        try:
            logger.info("fundamental_ingest.start", asset_class=asset_class)

            from fin_scraper.scrapers.stocks import StockScraper
            from fin_scraper.scrapers.crypto import CryptoScraper

            results = {"assets_updated": 0, "errors": 0}

            # Stocks
            if asset_class is None or asset_class == "STOCKS":
                stock_scraper = StockScraper(db)
                for ticker in stock_scraper._get_active_tickers():
                    try:
                        stock_scraper.fetch_fundamentals(ticker)
                        results["assets_updated"] += 1
                    except Exception as e:
                        logger.error("fundamental_ingest.stock_error", ticker=ticker, error=str(e))
                        results["errors"] += 1

            # Crypto
            if asset_class is None or asset_class == "CRYPTO":
                crypto_scraper = CryptoScraper(db)
                for token in crypto_scraper._get_active_tokens():
                    try:
                        crypto_scraper.fetch_fundamentals(token)
                        results["assets_updated"] += 1
                    except Exception as e:
                        logger.error("fundamental_ingest.crypto_error", token=token, error=str(e))
                        results["errors"] += 1

            complete_run(db, run, summary=str(results))
            return results

        except Exception as e:
            fail_run(db, run, error=str(e))
            raise
