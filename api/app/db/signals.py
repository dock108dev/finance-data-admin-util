"""Signal and analysis models — alpha signals, narratives, sentiment.

Equivalent to sports-data-admin's flow.py (game_stories, timeline_artifacts).

Mapping:
    sports_game_stories          → fin_market_analyses
    sports_game_timeline_artifacts → fin_session_timelines
    (positive EV logic)          → fin_alpha_signals
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


# ── Alpha Signals (equiv. +EV bets) ─────────────────────────────────────────

class AlphaSignal(Base, TimestampMixin):
    """A detected alpha opportunity — equivalent to +EV bet identification.

    Signal types:
    - CROSS_EXCHANGE_ARB:  Price discrepancy across exchanges
    - TECHNICAL_BREAKOUT:  Indicator convergence (RSI + MACD + BB)
    - SENTIMENT_DIVERGENCE: Social sentiment vs. price action mismatch
    - WHALE_ACCUMULATION:  On-chain whale buying detection
    - VOLUME_ANOMALY:      Unusual volume spike
    - MOMENTUM_SHIFT:      Trend reversal indicators
    - FUNDAMENTAL_MISPRICING: Price vs. fundamentals divergence
    """

    __tablename__ = "fin_alpha_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("fin_assets.id"), nullable=False)
    asset_class_id: Mapped[int] = mapped_column(ForeignKey("fin_asset_classes.id"), nullable=False)

    # Signal identity
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    signal_subtype: Mapped[str | None] = mapped_column(String(50))
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    # "LONG", "SHORT", "NEUTRAL"

    # Strength & confidence (equiv. EV% and confidence tier)
    strength: Mapped[float] = mapped_column(Float, nullable=False)
    # 0.0 to 1.0 (normalized signal strength)
    confidence_tier: Mapped[str] = mapped_column(String(10), nullable=False)
    # "HIGH", "MEDIUM", "LOW"
    ev_estimate: Mapped[float | None] = mapped_column(Float)
    # Expected value % if actionable

    # Context
    trigger_price: Mapped[float | None] = mapped_column(Float)
    target_price: Mapped[float | None] = mapped_column(Float)
    stop_loss: Mapped[float | None] = mapped_column(Float)
    risk_reward_ratio: Mapped[float | None] = mapped_column(Float)

    # Timing
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Resolution (did the signal play out?)
    outcome: Mapped[str | None] = mapped_column(String(20))
    # "HIT", "MISS", "EXPIRED", "PENDING"
    actual_return_pct: Mapped[float | None] = mapped_column(Float)

    # Disabled reason (equiv. ev_disabled_reason)
    disabled_reason: Mapped[str | None] = mapped_column(String(100))
    # "insufficient_data", "low_liquidity", "high_spread", "stale_reference"

    # Derivation details
    derivation: Mapped[dict | None] = mapped_column(JSONB)
    # Full breakdown of how signal was computed

    __table_args__ = (
        Index("idx_signals_asset_type", "asset_id", "signal_type"),
        Index("idx_signals_detected", "detected_at"),
        Index("idx_signals_confidence", "confidence_tier"),
        Index("idx_signals_outcome", "outcome"),
    )


# ── Market Analysis (equiv. Game Stories / Flow) ─────────────────────────────

class MarketAnalysis(Base, TimestampMixin):
    """AI-generated market narrative — equivalent to sports_game_stories.

    A structured analysis of a trading session with key moments,
    narrative blocks, and drama analysis.
    """

    __tablename__ = "fin_market_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("fin_assets.id"), nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("fin_sessions.id"))
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Content (equiv. moments_json + blocks_json)
    key_moments_json: Mapped[dict | None] = mapped_column(JSONB)
    # List of significant price/volume events
    narrative_blocks_json: Mapped[dict | None] = mapped_column(JSONB)
    # Structured narrative blocks (SETUP, CATALYST, REACTION, RESOLUTION)
    summary: Mapped[str | None] = mapped_column(Text)
    # Short-form summary

    # Analysis metadata
    analysis_version: Mapped[int] = mapped_column(Integer, default=1)
    generated_by: Mapped[str | None] = mapped_column(String(50))
    # "openai-gpt-4o", "manual"
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint(
            "asset_id", "analysis_date", "analysis_version",
            name="uq_market_analysis_identity"
        ),
    )


# ── Session Timelines (equiv. Timeline Artifacts) ───────────────────────────

class SessionTimeline(Base, TimestampMixin):
    """Merged timeline of session events — equivalent to timeline_artifacts.

    Combines candle data + social posts + signal events + news into
    a single chronological timeline for display.
    """

    __tablename__ = "fin_session_timelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("fin_sessions.id"), nullable=False)
    asset_id: Mapped[int] = mapped_column(ForeignKey("fin_assets.id"), nullable=False)

    # Timeline content
    timeline_json: Mapped[dict | None] = mapped_column(JSONB)
    # Chronological list of events: candles, social, signals, news
    market_analysis_json: Mapped[dict | None] = mapped_column(JSONB)
    # Drama analysis: key moments, volatility profile
    summary_json: Mapped[dict | None] = mapped_column(JSONB)
    # Session metadata summary

    # Generation info
    timeline_version: Mapped[int] = mapped_column(Integer, default=1)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generated_by: Mapped[str | None] = mapped_column(String(50))
    generation_reason: Mapped[str | None] = mapped_column(String(100))

    __table_args__ = (
        UniqueConstraint(
            "session_id", "asset_id", "timeline_version",
            name="uq_session_timeline_identity"
        ),
    )
