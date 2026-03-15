"""Sentiment mapper — maps social posts to assets by cashtag, aggregates sentiment snapshots."""

from datetime import datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)


class SentimentMapper:
    """Map social posts to assets and aggregate into sentiment snapshots."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def map_and_score(self, posts: list[dict]) -> dict:
        """Map posts to assets by cashtag, then aggregate sentiment.

        Args:
            posts: List of post dicts with 'cashtags' field.

        Returns:
            Summary dict.
        """
        mapped_count = 0
        asset_sentiments: dict[int, list[float]] = {}  # asset_id -> [scores]

        # Build ticker → asset_id lookup
        ticker_map = self._build_ticker_map()

        for post in posts:
            cashtags = post.get("cashtags", [])
            if not cashtags:
                continue

            for tag in cashtags:
                asset_id = ticker_map.get(tag)
                if asset_id is None:
                    continue

                # Update the post's asset_id and mapping_status
                self.db.execute(
                    text("""
                        UPDATE fin_social_posts
                        SET asset_id = :asset_id, mapping_status = 'mapped'
                        WHERE platform = :platform AND external_post_id = :ext_id
                            AND mapping_status = 'unmapped'
                    """),
                    {
                        "asset_id": asset_id,
                        "platform": post["platform"],
                        "ext_id": post["external_post_id"],
                    },
                )

                score = post.get("sentiment_score", 0.0)
                asset_sentiments.setdefault(asset_id, []).append(score)
                mapped_count += 1

        self.db.commit()

        # Create sentiment snapshots for each asset
        snapshots_created = 0
        for asset_id, scores in asset_sentiments.items():
            self._create_sentiment_snapshot(asset_id, scores)
            snapshots_created += 1

        self.db.commit()

        result = {
            "posts_mapped": mapped_count,
            "snapshots_created": snapshots_created,
        }
        logger.info("sentiment_mapper.complete", **result)
        return result

    def _build_ticker_map(self) -> dict[str, int]:
        """Build ticker -> asset_id map for all active assets."""
        result = self.db.execute(
            text(
                "SELECT id, ticker FROM fin_assets WHERE is_active = true"
            ),
        )
        return {row[1]: row[0] for row in result.fetchall()}

    def _create_sentiment_snapshot(self, asset_id: int, scores: list[float]) -> None:
        """Create an aggregated sentiment snapshot for an asset."""
        if not scores:
            return

        bullish = sum(1 for s in scores if s > 0.1)
        bearish = sum(1 for s in scores if s < -0.1)
        neutral = len(scores) - bullish - bearish
        total = len(scores)

        weighted = sum(scores) / total if total > 0 else 0

        # Get asset_class_id
        result = self.db.execute(
            text("SELECT asset_class_id FROM fin_assets WHERE id = :id"),
            {"id": asset_id},
        )
        row = result.fetchone()
        asset_class_id = row[0] if row else None

        self.db.execute(
            text("""
                INSERT INTO fin_sentiment_snapshots
                    (asset_id, asset_class_id, social_volume, bullish_pct, bearish_pct,
                     neutral_pct, weighted_sentiment, reddit_sentiment,
                     observed_at, window_minutes, source)
                VALUES
                    (:asset_id, :asset_class_id, :social_volume, :bullish_pct, :bearish_pct,
                     :neutral_pct, :weighted_sentiment, :reddit_sentiment,
                     :observed_at, 60, 'reddit')
            """),
            {
                "asset_id": asset_id,
                "asset_class_id": asset_class_id,
                "social_volume": total,
                "bullish_pct": round(bullish / total * 100, 1) if total else 0,
                "bearish_pct": round(bearish / total * 100, 1) if total else 0,
                "neutral_pct": round(neutral / total * 100, 1) if total else 0,
                "weighted_sentiment": round(weighted, 4),
                "reddit_sentiment": round(weighted, 4),
                "observed_at": datetime.now(timezone.utc),
            },
        )
