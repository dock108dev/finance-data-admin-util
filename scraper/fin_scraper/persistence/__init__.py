"""Data persistence layer — batch upsert operations for scraped data."""

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)


def batch_upsert_candles(db: Session, candles: list[dict]) -> int:
    """Batch upsert OHLCV candles. Returns count of rows affected."""
    if not candles:
        return 0

    created = 0
    for candle in candles:
        result = db.execute(
            text("""
                INSERT INTO fin_candles
                    (asset_id, session_id, timestamp, interval,
                     open, high, low, close, volume, vwap, source)
                VALUES
                    (:asset_id, :session_id, :timestamp, :interval,
                     :open, :high, :low, :close, :volume, :vwap, :source)
                ON CONFLICT ON CONSTRAINT uq_candle_identity
                DO UPDATE SET
                    open = EXCLUDED.open, high = EXCLUDED.high,
                    low = EXCLUDED.low, close = EXCLUDED.close,
                    volume = EXCLUDED.volume, vwap = EXCLUDED.vwap
                RETURNING id
            """),
            candle,
        )
        if result.fetchone():
            created += 1

    db.commit()
    logger.info("persistence.candles_upserted", count=created, total=len(candles))
    return created


def batch_upsert_prices(db: Session, prices: list[dict]) -> int:
    """Batch upsert exchange prices. Returns count of rows affected."""
    if not prices:
        return 0

    created = 0
    for price in prices:
        result = db.execute(
            text("""
                INSERT INTO fin_exchange_prices
                    (asset_id, exchange, pair_key, price, bid, ask,
                     volume_24h, observed_at)
                VALUES
                    (:asset_id, :exchange, :pair_key, :price, :bid, :ask,
                     :volume_24h, :observed_at)
                ON CONFLICT ON CONSTRAINT uq_exchange_price_identity
                DO UPDATE SET
                    price = EXCLUDED.price, bid = EXCLUDED.bid,
                    ask = EXCLUDED.ask, volume_24h = EXCLUDED.volume_24h,
                    observed_at = EXCLUDED.observed_at
                RETURNING id
            """),
            price,
        )
        if result.fetchone():
            created += 1

    db.commit()
    logger.info("persistence.prices_upserted", count=created, total=len(prices))
    return created


def batch_insert_social_posts(db: Session, posts: list[dict]) -> int:
    """Batch insert social posts (skip duplicates). Returns new row count."""
    if not posts:
        return 0

    created = 0
    for post in posts:
        result = db.execute(
            text("""
                INSERT INTO fin_social_posts
                    (platform, external_post_id, author, text,
                     sentiment_score, sentiment_label, posted_at, mapping_status)
                VALUES
                    (:platform, :external_post_id, :author, :text,
                     :sentiment_score, :sentiment_label, :posted_at, 'unmapped')
                ON CONFLICT (platform, external_post_id) DO NOTHING
                RETURNING id
            """),
            post,
        )
        if result.fetchone():
            created += 1

    db.commit()
    logger.info("persistence.social_posts_inserted", count=created, total=len(posts))
    return created
