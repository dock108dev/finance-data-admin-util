"""Market data models — assets, prices, sessions, candles.

Equivalent to sports-data-admin's sports.py (leagues, teams, games, plays, boxscores).

Mapping:
    sports_leagues     → fin_asset_classes
    sports_teams       → fin_assets
    sports_games       → fin_sessions
    sports_game_plays  → fin_candles (OHLCV ticks)
    sports_team_boxscores → fin_session_summaries
    sports_player_boxscores → fin_asset_fundamentals
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


# ── Asset Classes (equiv. Leagues) ───────────────────────────────────────────

class AssetClass(Base, TimestampMixin):
    """STOCKS, CRYPTO — equivalent to sports_leagues."""

    __tablename__ = "fin_asset_classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Relationships
    assets: Mapped[list["Asset"]] = relationship(back_populates="asset_class")


# ── Assets (equiv. Teams) ────────────────────────────────────────────────────

class Asset(Base, TimestampMixin):
    """Individual tradeable asset — AAPL, BTC, ETH, etc.

    Equivalent to sports_teams.
    """

    __tablename__ = "fin_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_class_id: Mapped[int] = mapped_column(ForeignKey("fin_asset_classes.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Metadata
    sector: Mapped[str | None] = mapped_column(String(100))       # "Technology", "DeFi"
    industry: Mapped[str | None] = mapped_column(String(100))     # "Software", "Layer 1"
    market_cap: Mapped[float | None] = mapped_column(Float)
    exchange: Mapped[str | None] = mapped_column(String(50))      # "NASDAQ", "Binance"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # External identifiers (equiv. external_codes JSONB)
    external_ids: Mapped[dict | None] = mapped_column(JSONB)
    # e.g. {"coingecko_id": "bitcoin", "cmc_id": 1, "polygon_ticker": "X:BTCUSD"}

    # Social handles
    twitter_handle: Mapped[str | None] = mapped_column(String(100))
    subreddit: Mapped[str | None] = mapped_column(String(100))

    # Branding
    logo_url: Mapped[str | None] = mapped_column(String(500))
    color_hex: Mapped[str | None] = mapped_column(String(7))

    # Tracking
    last_price_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_fundamental_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_social_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    asset_class: Mapped["AssetClass"] = relationship(back_populates="assets")

    __table_args__ = (
        UniqueConstraint("asset_class_id", "ticker", name="uq_asset_class_ticker"),
        Index("idx_assets_ticker", "ticker"),
        Index("idx_assets_class_active", "asset_class_id", "is_active"),
    )


# ── Market Sessions (equiv. Games) ──────────────────────────────────────────

class MarketSession(Base, TimestampMixin):
    """A trading session / window — equivalent to sports_games.

    For stocks: one per trading day per asset.
    For crypto: rolling 24h windows or user-defined intervals.
    """

    __tablename__ = "fin_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("fin_assets.id"), nullable=False)
    asset_class_id: Mapped[int] = mapped_column(ForeignKey("fin_asset_classes.id"), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Session timing
    open_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # OHLCV summary (equiv. to scores)
    open_price: Mapped[float | None] = mapped_column(Float)
    high_price: Mapped[float | None] = mapped_column(Float)
    low_price: Mapped[float | None] = mapped_column(Float)
    close_price: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)
    vwap: Mapped[float | None] = mapped_column(Float)

    # Derived metrics
    change_pct: Mapped[float | None] = mapped_column(Float)       # Daily % change
    range_pct: Mapped[float | None] = mapped_column(Float)        # (high-low)/open
    dollar_volume: Mapped[float | None] = mapped_column(Float)

    # Status (equiv. game status: scheduled → live → final)
    status: Mapped[str] = mapped_column(
        String(20), default="scheduled", nullable=False
    )  # scheduled, premarket, live, afterhours, closed

    # Raw data
    raw_data: Mapped[dict | None] = mapped_column(JSONB)

    # Tracking
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("asset_id", "session_date", name="uq_asset_session_date"),
        Index("idx_sessions_class_date", "asset_class_id", "session_date"),
        Index("idx_sessions_status", "status"),
    )


# ── Candles / Tick Data (equiv. Play-by-Play) ───────────────────────────────

class Candle(Base):
    """OHLCV candle — equivalent to sports_game_plays.

    Immutable time-series data. One row per (asset, interval, timestamp).
    """

    __tablename__ = "fin_candles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("fin_assets.id"), nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("fin_sessions.id"))

    # Time
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    interval: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # "1m", "5m", "15m", "1h", "1d"

    # OHLCV
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)

    # Optional enrichments
    vwap: Mapped[float | None] = mapped_column(Float)
    trade_count: Mapped[int | None] = mapped_column(Integer)

    # Source
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # "yfinance", "binance"
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint("asset_id", "interval", "timestamp", name="uq_candle_identity"),
        Index("idx_candles_asset_time", "asset_id", "timestamp"),
        Index("idx_candles_interval", "interval"),
    )


# ── Session Summaries (equiv. Team Boxscores) ───────────────────────────────

class SessionSummary(Base, TimestampMixin):
    """Aggregated session stats — equivalent to sports_team_boxscores.

    Computed from candles + external data after session close.
    """

    __tablename__ = "fin_session_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("fin_sessions.id"), nullable=False)
    asset_id: Mapped[int] = mapped_column(ForeignKey("fin_assets.id"), nullable=False)

    # Summary stats
    total_volume: Mapped[float | None] = mapped_column(Float)
    total_trades: Mapped[int | None] = mapped_column(Integer)
    avg_spread: Mapped[float | None] = mapped_column(Float)
    volatility: Mapped[float | None] = mapped_column(Float)  # Intraday std dev
    max_drawdown: Mapped[float | None] = mapped_column(Float)

    # Technical indicators (end-of-session)
    rsi_14: Mapped[float | None] = mapped_column(Float)
    macd_signal: Mapped[float | None] = mapped_column(Float)
    bb_upper: Mapped[float | None] = mapped_column(Float)
    bb_lower: Mapped[float | None] = mapped_column(Float)

    # Raw stats blob
    raw_stats_json: Mapped[dict | None] = mapped_column(JSONB)
    source: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        UniqueConstraint("session_id", "asset_id", name="uq_session_summary"),
    )


# ── Asset Fundamentals (equiv. Player Boxscores) ────────────────────────────

class AssetFundamental(Base, TimestampMixin):
    """Fundamental data points — equivalent to sports_player_boxscores.

    Periodic snapshots of fundamental metrics (P/E, market cap, TVL, etc.).
    """

    __tablename__ = "fin_asset_fundamentals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("fin_assets.id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Stock fundamentals
    pe_ratio: Mapped[float | None] = mapped_column(Float)
    eps: Mapped[float | None] = mapped_column(Float)
    dividend_yield: Mapped[float | None] = mapped_column(Float)
    revenue: Mapped[float | None] = mapped_column(Float)
    profit_margin: Mapped[float | None] = mapped_column(Float)

    # Crypto fundamentals
    tvl: Mapped[float | None] = mapped_column(Float)           # Total Value Locked
    circulating_supply: Mapped[float | None] = mapped_column(Float)
    max_supply: Mapped[float | None] = mapped_column(Float)
    active_addresses_24h: Mapped[int | None] = mapped_column(Integer)
    txn_volume_24h: Mapped[float | None] = mapped_column(Float)

    # Universal
    market_cap: Mapped[float | None] = mapped_column(Float)
    fully_diluted_valuation: Mapped[float | None] = mapped_column(Float)

    # Raw blob
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    source: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        UniqueConstraint("asset_id", "snapshot_date", name="uq_asset_fundamental_date"),
        Index("idx_fundamentals_asset", "asset_id"),
    )
