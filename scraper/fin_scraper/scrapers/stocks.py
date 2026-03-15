"""Stock data scraper — yfinance-based OHLCV and fundamentals ingestion.

Fetches daily/intraday candles and fundamental data for tracked US equities,
persists to fin_candles, fin_sessions, and fin_asset_fundamentals.
"""

from datetime import date, datetime, timezone
from typing import Any

import structlog
import yfinance as yf
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)

# STOCKS asset_class_id = 1
_STOCKS_CLASS_ID = 1


class StockScraper:
    """Scraper for US equity data via yfinance.

    Data flow: [yfinance] → normalize → validate → persist
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def ingest_daily(self, tickers: list[str] | None = None) -> dict:
        """Ingest end-of-day OHLCV for tracked stocks."""
        if tickers is None:
            tickers = self._get_active_tickers()

        results = {"processed": 0, "created": 0, "updated": 0, "errors": 0}

        for ticker in tickers:
            try:
                candles = self._fetch_daily_candles(ticker)
                if candles:
                    created = self._persist_candles(ticker, candles)
                    self._update_session(ticker, candles)
                    results["processed"] += 1
                    results["created"] += created
                else:
                    logger.warning("stock_scraper.no_data", ticker=ticker)
            except Exception as e:
                logger.error("stock_scraper.error", ticker=ticker, error=str(e))
                results["errors"] += 1

        return results

    def ingest_intraday(self, tickers: list[str] | None = None,
                        interval: str = "5m") -> dict:
        """Ingest intraday candles for active trading hours."""
        if tickers is None:
            tickers = self._get_active_tickers()

        results = {"processed": 0, "created": 0}

        for ticker in tickers:
            try:
                candles = self._fetch_intraday_candles(ticker, interval)
                if candles:
                    created = self._persist_candles(ticker, candles)
                    results["processed"] += 1
                    results["created"] += created
            except Exception as e:
                logger.error("stock_scraper.intraday_error", ticker=ticker, error=str(e))

        return results

    def fetch_fundamentals(self, ticker: str) -> dict[str, Any]:
        """Fetch and persist fundamental data for a stock."""
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info or "symbol" not in info:
            logger.warning("stock_scraper.no_fundamentals", ticker=ticker)
            return {}

        fundamentals = {
            "pe_ratio": info.get("trailingPE"),
            "eps": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "revenue": info.get("totalRevenue"),
            "profit_margin": info.get("profitMargins"),
            "market_cap": info.get("marketCap"),
            "fully_diluted_valuation": info.get("enterpriseValue"),
        }

        self._persist_fundamentals(ticker, fundamentals)
        return fundamentals

    # ── Private Methods ──────────────────────────────────────────────────

    def _get_active_tickers(self) -> list[str]:
        """Query active stock tickers from database."""
        result = self.db.execute(
            text(
                "SELECT ticker FROM fin_assets "
                "WHERE asset_class_id = :class_id AND is_active = true "
                "ORDER BY ticker"
            ),
            {"class_id": _STOCKS_CLASS_ID},
        )
        return [row[0] for row in result.fetchall()]

    def _get_asset_id(self, ticker: str) -> int | None:
        """Look up asset ID for a ticker."""
        result = self.db.execute(
            text(
                "SELECT id FROM fin_assets "
                "WHERE ticker = :ticker AND asset_class_id = :class_id"
            ),
            {"ticker": ticker, "class_id": _STOCKS_CLASS_ID},
        )
        row = result.fetchone()
        return row[0] if row else None

    def _fetch_daily_candles(self, ticker: str) -> list[dict]:
        """Fetch daily OHLCV from yfinance (last 5 days)."""
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")

        if hist.empty:
            return []

        return [
            {
                "timestamp": row.name.to_pydatetime().replace(tzinfo=timezone.utc),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
                "interval": "1d",
                "source": "yfinance",
            }
            for _, row in hist.iterrows()
        ]

    def _fetch_intraday_candles(self, ticker: str, interval: str) -> list[dict]:
        """Fetch intraday candles from yfinance."""
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d", interval=interval)

        if hist.empty:
            return []

        return [
            {
                "timestamp": row.name.to_pydatetime().replace(tzinfo=timezone.utc),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
                "interval": interval,
                "source": "yfinance",
            }
            for _, row in hist.iterrows()
        ]

    def _persist_candles(self, ticker: str, candles: list[dict]) -> int:
        """Persist candles to fin_candles table (upsert). Returns count created."""
        asset_id = self._get_asset_id(ticker)
        if asset_id is None:
            logger.warning("stock_scraper.unknown_ticker", ticker=ticker)
            return 0

        created = 0
        for candle in candles:
            result = self.db.execute(
                text("""
                    INSERT INTO fin_candles
                        (asset_id, timestamp, interval, open, high, low, close, volume, source)
                    VALUES
                        (:asset_id, :timestamp, :interval, :open, :high, :low, :close, :volume, :source)
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
            "stock_scraper.candles_persisted",
            ticker=ticker,
            created=created,
            total=len(candles),
        )
        return created

    def _update_session(self, ticker: str, candles: list[dict]) -> None:
        """Update or create fin_sessions record with OHLCV summary."""
        asset_id = self._get_asset_id(ticker)
        if asset_id is None or not candles:
            return

        # Group candles by date for session creation
        by_date: dict[date, list[dict]] = {}
        for c in candles:
            d = c["timestamp"].date()
            by_date.setdefault(d, []).append(c)

        for session_date, day_candles in by_date.items():
            opens = [c["open"] for c in day_candles]
            highs = [c["high"] for c in day_candles]
            lows = [c["low"] for c in day_candles]
            closes = [c["close"] for c in day_candles]
            volumes = [c["volume"] for c in day_candles]

            open_price = opens[0]
            close_price = closes[-1]
            high_price = max(highs)
            low_price = min(lows)
            total_volume = sum(volumes)
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
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume,
                        change_pct = EXCLUDED.change_pct,
                        range_pct = EXCLUDED.range_pct,
                        status = EXCLUDED.status,
                        last_scraped_at = EXCLUDED.last_scraped_at,
                        updated_at = NOW()
                """),
                {
                    "asset_id": asset_id,
                    "class_id": _STOCKS_CLASS_ID,
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
        logger.info("stock_scraper.sessions_updated", ticker=ticker, sessions=len(by_date))

    def _persist_fundamentals(self, ticker: str, data: dict) -> None:
        """Persist fundamentals to fin_asset_fundamentals."""
        asset_id = self._get_asset_id(ticker)
        if asset_id is None:
            return

        today = date.today()
        self.db.execute(
            text("""
                INSERT INTO fin_asset_fundamentals
                    (asset_id, snapshot_date, pe_ratio, eps, dividend_yield,
                     revenue, profit_margin, market_cap, fully_diluted_valuation, source)
                VALUES
                    (:asset_id, :snapshot_date, :pe_ratio, :eps, :dividend_yield,
                     :revenue, :profit_margin, :market_cap, :fdv, :source)
                ON CONFLICT (asset_id, snapshot_date) DO UPDATE SET
                    pe_ratio = EXCLUDED.pe_ratio,
                    eps = EXCLUDED.eps,
                    dividend_yield = EXCLUDED.dividend_yield,
                    revenue = EXCLUDED.revenue,
                    profit_margin = EXCLUDED.profit_margin,
                    market_cap = EXCLUDED.market_cap,
                    fully_diluted_valuation = EXCLUDED.fully_diluted_valuation,
                    updated_at = NOW()
            """),
            {
                "asset_id": asset_id,
                "snapshot_date": today,
                "pe_ratio": data.get("pe_ratio"),
                "eps": data.get("eps"),
                "dividend_yield": data.get("dividend_yield"),
                "revenue": data.get("revenue"),
                "profit_margin": data.get("profit_margin"),
                "market_cap": data.get("market_cap"),
                "fdv": data.get("fully_diluted_valuation"),
                "source": "yfinance",
            },
        )
        self.db.commit()

        # Update last_fundamental_at
        self.db.execute(
            text(
                "UPDATE fin_assets SET last_fundamental_at = :now, updated_at = :now "
                "WHERE id = :asset_id"
            ),
            {"asset_id": asset_id, "now": datetime.now(timezone.utc)},
        )
        self.db.commit()
