"""Exchange price synchronizer — cross-exchange price sync for arb detection.

Fetches prices from Binance (primary), upserts to fin_exchange_prices
and fin_arbitrage_work for real-time arbitrage detection.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from fin_scraper.clients.binance_client import BinanceClient

logger = structlog.get_logger(__name__)

_CRYPTO_CLASS_ID = 2


@dataclass
class NormalizedPrice:
    """Normalized price snapshot from any exchange."""
    asset_ticker: str
    exchange: str
    price: float
    bid: float | None = None
    ask: float | None = None
    volume_24h: float | None = None
    observed_at: datetime | None = None


class ExchangePriceSynchronizer:
    """Orchestrates cross-exchange price syncing for arb detection.

    Flow:
    1. Fetch prices from exchange clients
    2. Normalize to NormalizedPrice
    3. Match to assets in database (by ticker)
    4. Upsert to fin_exchange_prices (historical)
    5. Upsert to fin_arbitrage_work (real-time comparison)
    """

    def __init__(self, db_session: Session, asset_class: str = "CRYPTO"):
        self.db = db_session
        self.asset_class = asset_class

    def sync_all(self) -> dict:
        """Sync prices from all configured exchanges."""
        results = {
            "exchanges_synced": 0,
            "prices_upserted": 0,
            "arb_entries_upserted": 0,
            "errors": 0,
        }

        # Get active crypto tokens
        tokens = self._get_active_tokens()
        if not tokens:
            return results

        # Fetch from Binance (primary exchange)
        binance = BinanceClient()
        try:
            for token in tokens:
                try:
                    ticker_data = binance.get_24h_ticker(token)
                    book_data = binance.get_book_ticker(token)

                    normalized = NormalizedPrice(
                        asset_ticker=token,
                        exchange="Binance",
                        price=ticker_data["price"],
                        bid=book_data["bid"],
                        ask=book_data["ask"],
                        volume_24h=ticker_data.get("volume_24h"),
                        observed_at=datetime.now(timezone.utc),
                    )

                    self._upsert_exchange_prices([normalized])
                    self._upsert_arb_work([normalized])
                    results["prices_upserted"] += 1

                except Exception as e:
                    logger.error(
                        "exchange_sync.token_error",
                        token=token,
                        error=str(e),
                    )
                    # Rollback failed transaction so next token can proceed
                    self.db.rollback()
                    results["errors"] += 1

            results["exchanges_synced"] = 1
        finally:
            binance.close()

        return results

    def _get_active_tokens(self) -> list[str]:
        """Get active crypto tokens."""
        result = self.db.execute(
            text(
                "SELECT ticker FROM fin_assets "
                "WHERE asset_class_id = :class_id AND is_active = true "
                "ORDER BY ticker"
            ),
            {"class_id": _CRYPTO_CLASS_ID},
        )
        # Filter to tokens that Binance supports
        all_tokens = [row[0] for row in result.fetchall()]
        return [t for t in all_tokens if t in BinanceClient.PAIR_MAP]

    def _get_asset_id(self, ticker: str) -> int | None:
        """Look up asset ID."""
        result = self.db.execute(
            text(
                "SELECT id FROM fin_assets "
                "WHERE ticker = :ticker AND asset_class_id = :class_id"
            ),
            {"ticker": ticker, "class_id": _CRYPTO_CLASS_ID},
        )
        row = result.fetchone()
        return row[0] if row else None

    def _upsert_exchange_prices(self, prices: list[NormalizedPrice]) -> None:
        """Upsert to fin_exchange_prices (historical record).

        Opening price: INSERT ... ON CONFLICT DO NOTHING
        Latest price: INSERT ... ON CONFLICT DO UPDATE
        """
        for p in prices:
            asset_id = self._get_asset_id(p.asset_ticker)
            if asset_id is None:
                continue

            spread = (p.ask - p.bid) if p.bid and p.ask else None
            mid = ((p.ask + p.bid) / 2) if p.bid and p.ask else p.price
            spread_pct = (spread / mid * 100) if spread and mid else None

            # Latest price (upsert — always update)
            self.db.execute(
                text("""
                    INSERT INTO fin_exchange_prices
                        (asset_id, exchange, price_type, price, bid, ask,
                         spread, spread_pct, volume_24h, observed_at, is_closing)
                    VALUES
                        (:asset_id, :exchange, 'spot', :price, :bid, :ask,
                         :spread, :spread_pct, :volume_24h, :observed_at, false)
                    ON CONFLICT (asset_id, exchange, price_type, is_closing) DO UPDATE SET
                        price = EXCLUDED.price,
                        bid = EXCLUDED.bid,
                        ask = EXCLUDED.ask,
                        spread = EXCLUDED.spread,
                        spread_pct = EXCLUDED.spread_pct,
                        volume_24h = EXCLUDED.volume_24h,
                        observed_at = EXCLUDED.observed_at
                """),
                {
                    "asset_id": asset_id,
                    "exchange": p.exchange,
                    "price": p.price,
                    "bid": p.bid,
                    "ask": p.ask,
                    "spread": spread,
                    "spread_pct": spread_pct,
                    "volume_24h": p.volume_24h,
                    "observed_at": p.observed_at,
                },
            )

        self.db.commit()

    def _upsert_arb_work(self, prices: list[NormalizedPrice]) -> None:
        """Upsert to fin_arbitrage_work (ephemeral comparison table).

        Computes spread vs reference exchange (Binance as reference).
        """
        for p in prices:
            asset_id = self._get_asset_id(p.asset_ticker)
            if asset_id is None:
                continue

            pair_key = f"{p.asset_ticker}USDT"

            self.db.execute(
                text("""
                    INSERT INTO fin_arbitrage_work
                        (asset_id, pair_key, exchange, price, bid, ask,
                         volume_24h, spread_vs_reference, arb_pct,
                         reference_exchange, observed_at, market_category)
                    VALUES
                        (:asset_id, :pair_key, :exchange, :price, :bid, :ask,
                         :volume_24h, 0, 0,
                         'Binance', :observed_at, 'spot')
                    ON CONFLICT (asset_id, pair_key, exchange) DO UPDATE SET
                        price = EXCLUDED.price,
                        bid = EXCLUDED.bid,
                        ask = EXCLUDED.ask,
                        volume_24h = EXCLUDED.volume_24h,
                        observed_at = EXCLUDED.observed_at
                """),
                {
                    "asset_id": asset_id,
                    "pair_key": pair_key,
                    "exchange": p.exchange,
                    "price": p.price,
                    "bid": p.bid,
                    "ask": p.ask,
                    "volume_24h": p.volume_24h,
                    "observed_at": p.observed_at,
                },
            )

        self.db.commit()
