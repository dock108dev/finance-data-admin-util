"""Fear & Greed Index collector — Alternative.me API.

Fetches the Crypto Fear & Greed Index and persists to fin_sentiment_snapshots.
"""

from datetime import datetime, timezone

import httpx
import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)

FEAR_GREED_URL = "https://api.alternative.me/fng/"


class FearGreedCollector:
    """Fetch and persist the Crypto Fear & Greed Index."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def collect(self, limit: int = 1) -> dict:
        """Fetch Fear & Greed Index and persist as a market-wide sentiment snapshot.

        Args:
            limit: Number of historical data points (1 = latest only).

        Returns:
            Summary dict.
        """
        try:
            resp = httpx.get(FEAR_GREED_URL, params={"limit": limit}, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("fear_greed.fetch_error", error=str(e))
            return {"error": str(e)}

        entries = data.get("data", [])
        created = 0

        for entry in entries:
            value = int(entry.get("value", 50))
            classification = entry.get("value_classification", "Neutral")
            timestamp = datetime.fromtimestamp(
                int(entry.get("timestamp", 0)), tz=timezone.utc
            )

            # Map fear/greed to bullish/bearish percentages
            bullish_pct = value  # 0-100 scale: 0=extreme fear, 100=extreme greed
            bearish_pct = 100 - value

            # Persist as a CRYPTO asset_class-level snapshot (no specific asset)
            result = self.db.execute(
                text("""
                    INSERT INTO fin_sentiment_snapshots
                        (asset_class_id, fear_greed_index, bullish_pct, bearish_pct,
                         observed_at, window_minutes, source,
                         raw_data)
                    VALUES
                        (2, :fear_greed, :bullish_pct, :bearish_pct,
                         :observed_at, 1440, 'alternative.me',
                         :raw_data)
                """),
                {
                    "fear_greed": value,
                    "bullish_pct": bullish_pct,
                    "bearish_pct": bearish_pct,
                    "observed_at": timestamp,
                    "raw_data": str({"value": value, "classification": classification}),
                },
            )
            created += 1

        self.db.commit()
        logger.info("fear_greed.collected", entries=created)
        return {"entries_created": created}
