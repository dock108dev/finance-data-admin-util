"""Exchange price models — cross-exchange prices, arbitrage, spread tracking.

Equivalent to sports-data-admin's odds.py (game_odds + fairbet_work).

Mapping:
    sports_game_odds         → fin_exchange_prices
    fairbet_game_odds_work   → fin_arbitrage_work
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


# ── Exchange Prices (equiv. Game Odds) ───────────────────────────────────────

class ExchangePrice(Base):
    """Price snapshot from a specific exchange — equivalent to sports_game_odds.

    One row per (asset, exchange, price_type, timestamp bucket).
    Tracks bid/ask/last across all exchanges for comparison.
    """

    __tablename__ = "fin_exchange_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("fin_assets.id"), nullable=False)
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "Binance", "Coinbase", "NYSE", "NASDAQ"

    # Price data
    price_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # "spot", "bid", "ask", "last", "mid"
    price: Mapped[float] = mapped_column(Float, nullable=False)
    volume_24h: Mapped[float | None] = mapped_column(Float)

    # Spread info
    bid: Mapped[float | None] = mapped_column(Float)
    ask: Mapped[float | None] = mapped_column(Float)
    spread: Mapped[float | None] = mapped_column(Float)       # ask - bid
    spread_pct: Mapped[float | None] = mapped_column(Float)   # spread / mid

    # Observation
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_closing: Mapped[bool] = mapped_column(Boolean, default=False)
    # True = end-of-session snapshot (equiv. closing line)

    # Raw
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint(
            "asset_id", "exchange", "price_type", "is_closing",
            name="uq_exchange_price_identity"
        ),
        Index("idx_exchange_prices_asset", "asset_id"),
        Index("idx_exchange_prices_observed", "observed_at"),
        Index("idx_exchange_prices_exchange", "exchange"),
    )


# ── Arbitrage Work Table (equiv. FairBet Work) ──────────────────────────────

class ArbitrageWork(Base):
    """Ephemeral cross-exchange comparison — equivalent to fairbet_game_odds_work.

    One row per (asset, pair_key, exchange). Continuously upserted during
    exchange sync. Cleared when opportunities resolve or expire.

    pair_key examples:
        "BTC/USD:spot"      — spot price comparison
        "ETH/BTC:spot"      — cross-pair comparison
        "AAPL:bid_ask"      — bid/ask spread comparison
    """

    __tablename__ = "fin_arbitrage_work"

    # Composite PK (equiv. to fairbet's composite key)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("fin_assets.id"), primary_key=True
    )
    pair_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    exchange: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Price
    price: Mapped[float] = mapped_column(Float, nullable=False)
    bid: Mapped[float | None] = mapped_column(Float)
    ask: Mapped[float | None] = mapped_column(Float)
    volume_24h: Mapped[float | None] = mapped_column(Float)

    # Arb metrics (computed at query time, cached here for display)
    spread_vs_reference: Mapped[float | None] = mapped_column(Float)
    arb_pct: Mapped[float | None] = mapped_column(Float)
    reference_exchange: Mapped[str | None] = mapped_column(String(50))

    # Observation
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Metadata
    market_category: Mapped[str | None] = mapped_column(String(50))
    # "spot", "futures", "options"

    __table_args__ = (
        Index("idx_arb_work_asset", "asset_id"),
        Index("idx_arb_work_observed", "observed_at"),
    )
