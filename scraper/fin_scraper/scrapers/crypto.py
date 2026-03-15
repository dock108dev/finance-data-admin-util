"""Crypto data scraper — Binance + CoinGecko based ingestion.

Fetches daily/intraday candles, exchange prices, and fundamentals
for tracked crypto assets.
"""

from datetime import date, datetime, timezone
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from fin_scraper.clients.binance_client import BinanceClient
from fin_scraper.clients.coingecko_client import CoinGeckoClient
from fin_scraper.config import get_settings

logger = structlog.get_logger(__name__)

# CRYPTO asset_class_id = 2
_CRYPTO_CLASS_ID = 2


class CryptoScraper:
    """Scraper for cryptocurrency market data via Binance + CoinGecko.

    Data flow: [Binance / CoinGecko] → normalize → validate → persist
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        settings = get_settings()
        self._binance = BinanceClient()
        self._coingecko = CoinGeckoClient(api_key=settings.coingecko_api_key)

    def ingest_daily(self, tokens: list[str] | None = None) -> dict:
        """Ingest end-of-day OHLCV for tracked crypto assets.

        Uses Binance for daily klines (preferred), falls back to CoinGecko.
        """
        if tokens is None:
            tokens = self._get_active_tokens()

        results = {"processed": 0, "created": 0, "errors": 0}

        for token in tokens:
            try:
                # Try Binance first (better data), fall back to CoinGecko
                try:
                    candles = self._fetch_binance_klines(token, "1d")
                except Exception:
                    logger.info("crypto_scraper.binance_fallback", token=token)
                    external_ids = self._get_external_ids(token)
                    candles = self._fetch_daily_from_coingecko(token, external_ids)

                if candles:
                    created = self._persist_candles(token, candles)
                    self._update_session(token, candles)
                    results["processed"] += 1
                    results["created"] += created
            except Exception as e:
                logger.error("crypto_scraper.error", token=token, error=str(e))
                results["errors"] += 1

        return results

    def ingest_intraday(self, tokens: list[str] | None = None,
                        interval: str = "5m") -> dict:
        """Ingest real-time candles from Binance."""
        if tokens is None:
            tokens = self._get_active_tokens()

        results = {"processed": 0, "created": 0}

        for token in tokens:
            try:
                candles = self._fetch_binance_klines(token, interval)
                if candles:
                    created = self._persist_candles(token, candles)
                    results["processed"] += 1
                    results["created"] += created
            except Exception as e:
                logger.error("crypto_scraper.intraday_error", token=token, error=str(e))

        return results

    def fetch_exchange_prices(self, token: str) -> list[dict]:
        """Fetch price from Binance for exchange price tracking."""
        prices = []
        try:
            ticker_data = self._binance.get_24h_ticker(token)
            prices.append(ticker_data)
        except Exception as e:
            logger.error("crypto_scraper.exchange_price_error", token=token, error=str(e))
        return prices

    def fetch_fundamentals(self, token: str) -> dict[str, Any]:
        """Fetch fundamental/on-chain data from CoinGecko."""
        external_ids = self._get_external_ids(token)

        try:
            data = self._coingecko.get_coin_data(token, external_ids)
        except Exception as e:
            logger.error("crypto_scraper.fundamentals_error", token=token, error=str(e))
            return {}

        self._persist_fundamentals(token, data)
        return data

    # ── Private Methods ──────────────────────────────────────────────────

    def _get_active_tokens(self) -> list[str]:
        """Query active crypto tickers from database."""
        result = self.db.execute(
            text(
                "SELECT ticker FROM fin_assets "
                "WHERE asset_class_id = :class_id AND is_active = true "
                "ORDER BY ticker"
            ),
            {"class_id": _CRYPTO_CLASS_ID},
        )
        return [row[0] for row in result.fetchall()]

    def _get_asset_id(self, ticker: str) -> int | None:
        """Look up asset ID for a ticker."""
        result = self.db.execute(
            text(
                "SELECT id FROM fin_assets "
                "WHERE ticker = :ticker AND asset_class_id = :class_id"
            ),
            {"ticker": ticker, "class_id": _CRYPTO_CLASS_ID},
        )
        row = result.fetchone()
        return row[0] if row else None

    def _get_external_ids(self, ticker: str) -> dict:
        """Get external_ids JSONB for a token."""
        result = self.db.execute(
            text(
                "SELECT external_ids FROM fin_assets "
                "WHERE ticker = :ticker AND asset_class_id = :class_id"
            ),
            {"ticker": ticker, "class_id": _CRYPTO_CLASS_ID},
        )
        row = result.fetchone()
        return row[0] if row and row[0] else {}

    def _fetch_binance_klines(self, token: str, interval: str) -> list[dict]:
        """Fetch kline data from Binance."""
        limit = 100 if interval in ("1m", "5m") else 5
        return self._binance.get_klines(token, interval=interval, limit=limit)

    def _fetch_daily_from_coingecko(self, token: str, external_ids: dict | None = None) -> list[dict]:
        """Fetch daily OHLCV from CoinGecko."""
        return self._coingecko.get_ohlc(token, days=7, external_ids=external_ids)

    def _persist_candles(self, token: str, candles: list[dict]) -> int:
        """Persist candles to fin_candles table (upsert). Returns count created."""
        asset_id = self._get_asset_id(token)
        if asset_id is None:
            logger.warning("crypto_scraper.unknown_token", token=token)
            return 0

        created = 0
        for candle in candles:
            result = self.db.execute(
                text("""
                    INSERT INTO fin_candles
                        (asset_id, timestamp, interval, open, high, low, close,
                         volume, trade_count, source)
                    VALUES
                        (:asset_id, :timestamp, :interval, :open, :high, :low, :close,
                         :volume, :trade_count, :source)
                    ON CONFLICT (asset_id, interval, timestamp) DO NOTHING
                    RETURNING id
                """),
                {
                    "asset_id": asset_id,
                    "timestamp": candle["timestamp"],
                    "interval": candle["interval"],
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "volume": candle["volume"],
                    "trade_count": candle.get("trade_count"),
                    "source": candle["source"],
                },
            )
            if result.fetchone() is not None:
                created += 1

        self.db.commit()

        # Update last_price_at on the asset
        self.db.execute(
            text(
                "UPDATE fin_assets SET last_price_at = :now, updated_at = :now "
                "WHERE id = :asset_id"
            ),
            {"asset_id": asset_id, "now": datetime.now(timezone.utc)},
        )
        self.db.commit()

        logger.info(
            "crypto_scraper.candles_persisted",
            token=token,
            created=created,
            total=len(candles),
        )
        return created

    def _update_session(self, token: str, candles: list[dict]) -> None:
        """Update or create fin_sessions record."""
        asset_id = self._get_asset_id(token)
        if asset_id is None or not candles:
            return

        by_date: dict[date, list[dict]] = {}
        for c in candles:
            d = c["timestamp"].date()
            by_date.setdefault(d, []).append(c)

        for session_date, day_candles in by_date.items():
            open_price = day_candles[0]["open"]
            close_price = day_candles[-1]["close"]
            high_price = max(c["high"] for c in day_candles)
            low_price = min(c["low"] for c in day_candles)
            total_volume = sum(c["volume"] for c in day_candles)
            change_pct = ((close_price - open_price) / open_price * 100) if open_price else 0
            range_pct = ((high_price - low_price) / low_price * 100) if low_price else 0

            self.db.execute(
                text("""
                    INSERT INTO fin_sessions
                        (asset_id, asset_class_id, session_date, open_price, high_price,
                         low_price, close_price, volume, change_pct, range_pct, status,
                         last_scraped_at)
                    VALUES
                        (:asset_id, :class_id, :session_date, :open, :high,
                         :low, :close, :volume, :change_pct, :range_pct, 'closed',
                         :now)
                    ON CONFLICT (asset_id, session_date) DO UPDATE SET
                        high_price = GREATEST(fin_sessions.high_price, EXCLUDED.high_price),
                        low_price = LEAST(fin_sessions.low_price, EXCLUDED.low_price),
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume,
                        change_pct = EXCLUDED.change_pct,
                        range_pct = EXCLUDED.range_pct,
                        last_scraped_at = EXCLUDED.last_scraped_at,
                        updated_at = NOW()
                """),
                {
                    "asset_id": asset_id,
                    "class_id": _CRYPTO_CLASS_ID,
                    "session_date": session_date,
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": total_volume,
                    "change_pct": change_pct,
                    "range_pct": range_pct,
                    "now": datetime.now(timezone.utc),
                },
            )

        self.db.commit()

    def _persist_fundamentals(self, token: str, data: dict) -> None:
        """Persist fundamentals to fin_asset_fundamentals."""
        asset_id = self._get_asset_id(token)
        if asset_id is None:
            return

        today = date.today()
        self.db.execute(
            text("""
                INSERT INTO fin_asset_fundamentals
                    (asset_id, snapshot_date, market_cap, fully_diluted_valuation,
                     circulating_supply, max_supply, tvl, source)
                VALUES
                    (:asset_id, :snapshot_date, :market_cap, :fdv,
                     :circulating_supply, :max_supply, :tvl, :source)
                ON CONFLICT (asset_id, snapshot_date) DO UPDATE SET
                    market_cap = EXCLUDED.market_cap,
                    fully_diluted_valuation = EXCLUDED.fully_diluted_valuation,
                    circulating_supply = EXCLUDED.circulating_supply,
                    max_supply = EXCLUDED.max_supply,
                    tvl = EXCLUDED.tvl,
                    updated_at = NOW()
            """),
            {
                "asset_id": asset_id,
                "snapshot_date": today,
                "market_cap": data.get("market_cap"),
                "fdv": data.get("fully_diluted_valuation"),
                "circulating_supply": data.get("circulating_supply"),
                "max_supply": data.get("max_supply"),
                "tvl": data.get("tvl"),
                "source": "coingecko",
            },
        )
        self.db.commit()

        self.db.execute(
            text(
                "UPDATE fin_assets SET last_fundamental_at = :now, updated_at = :now "
                "WHERE id = :asset_id"
            ),
            {"asset_id": asset_id, "now": datetime.now(timezone.utc)},
        )
        self.db.commit()
