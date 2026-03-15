"""Social and sentiment models — tweets, Reddit posts, news, Fear & Greed.

Equivalent to sports-data-admin's social.py (team_social_posts, team_social_accounts).

Mapping:
    team_social_posts    → fin_social_posts
    team_social_accounts → fin_social_accounts
    (new)                → fin_sentiment_snapshots
    (new)                → fin_news_articles
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
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


# ── Social Posts (equiv. team_social_posts) ──────────────────────────────────

class SocialPost(Base, TimestampMixin):
    """Social media post related to an asset — equivalent to team_social_posts."""

    __tablename__ = "fin_social_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("fin_assets.id"))
    session_id: Mapped[int | None] = mapped_column(ForeignKey("fin_sessions.id"))

    # Source
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    # "twitter", "reddit", "discord"
    external_post_id: Mapped[str] = mapped_column(String(100), nullable=False)
    post_url: Mapped[str | None] = mapped_column(String(500))
    author: Mapped[str | None] = mapped_column(String(200))
    author_followers: Mapped[int | None] = mapped_column(Integer)

    # Content
    text: Mapped[str | None] = mapped_column(Text)
    has_media: Mapped[bool] = mapped_column(Boolean, default=False)
    media_url: Mapped[str | None] = mapped_column(String(500))

    # Engagement
    likes_count: Mapped[int | None] = mapped_column(Integer)
    retweets_count: Mapped[int | None] = mapped_column(Integer)
    replies_count: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[int | None] = mapped_column(Integer)  # Reddit score

    # Sentiment
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    # -1.0 (bearish) to +1.0 (bullish)
    sentiment_label: Mapped[str | None] = mapped_column(String(20))
    # "bullish", "bearish", "neutral"

    # Mapping
    mapping_status: Mapped[str] = mapped_column(String(20), default="unmapped")
    # "unmapped", "mapped", "irrelevant"
    cashtags: Mapped[list | None] = mapped_column(JSONB)
    # e.g. ["$AAPL", "$TSLA"]

    # Timing
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Influence assessment
    is_influencer: Mapped[bool] = mapped_column(Boolean, default=False)
    influence_tier: Mapped[str | None] = mapped_column(String(10))
    # "whale", "influencer", "retail"

    __table_args__ = (
        UniqueConstraint("platform", "external_post_id", name="uq_social_post_identity"),
        Index("idx_social_posts_asset", "asset_id"),
        Index("idx_social_posts_posted", "posted_at"),
        Index("idx_social_posts_platform", "platform"),
        Index("idx_social_posts_mapping", "mapping_status"),
    )


# ── Social Accounts (equiv. team_social_accounts) ───────────────────────────

class SocialAccount(Base, TimestampMixin):
    """Tracked social account for an asset — equivalent to team_social_accounts."""

    __tablename__ = "fin_social_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("fin_assets.id"))

    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    handle: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # "official", "influencer", "analyst", "community"
    followers: Mapped[int | None] = mapped_column(Integer)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("platform", "handle", name="uq_social_account_identity"),
    )


# ── Sentiment Snapshots ─────────────────────────────────────────────────────

class SentimentSnapshot(Base):
    """Aggregated sentiment at a point in time — new model for financial context."""

    __tablename__ = "fin_sentiment_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("fin_assets.id"))
    asset_class_id: Mapped[int | None] = mapped_column(ForeignKey("fin_asset_classes.id"))

    # Scores
    fear_greed_index: Mapped[int | None] = mapped_column(Integer)
    # 0-100 (0=extreme fear, 100=extreme greed)
    social_volume: Mapped[int | None] = mapped_column(Integer)
    # Number of mentions in window
    bullish_pct: Mapped[float | None] = mapped_column(Float)
    bearish_pct: Mapped[float | None] = mapped_column(Float)
    neutral_pct: Mapped[float | None] = mapped_column(Float)
    weighted_sentiment: Mapped[float | None] = mapped_column(Float)
    # Follower-weighted sentiment (-1 to +1)

    # Source breakdown
    twitter_sentiment: Mapped[float | None] = mapped_column(Float)
    reddit_sentiment: Mapped[float | None] = mapped_column(Float)
    news_sentiment: Mapped[float | None] = mapped_column(Float)

    # Timing
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_minutes: Mapped[int] = mapped_column(Integer, default=60)

    # Raw
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    source: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        Index("idx_sentiment_asset_time", "asset_id", "observed_at"),
        Index("idx_sentiment_class_time", "asset_class_id", "observed_at"),
    )


# ── News Articles ────────────────────────────────────────────────────────────

class NewsArticle(Base, TimestampMixin):
    """News article related to an asset — extends social with structured news."""

    __tablename__ = "fin_news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("fin_assets.id"))

    # Article info
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    author: Mapped[str | None] = mapped_column(String(200))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Sentiment
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    sentiment_label: Mapped[str | None] = mapped_column(String(20))

    # Classification
    category: Mapped[str | None] = mapped_column(String(50))
    # "earnings", "merger", "regulation", "macro", "technical"
    tickers_mentioned: Mapped[list | None] = mapped_column(JSONB)

    # Raw
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint("url", name="uq_news_url"),
        Index("idx_news_asset", "asset_id"),
        Index("idx_news_published", "published_at"),
    )
