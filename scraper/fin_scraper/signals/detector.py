"""Signal detectors — identify alpha opportunities from market data.

Three detectors:
- ArbitrageDetector — cross-exchange price discrepancies
- VolumeAnomalyDetector — unusual volume spikes
- SentimentDivergenceDetector — sentiment vs price direction mismatch
"""

from datetime import datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)


class ArbitrageDetector:
    """Detect cross-exchange arbitrage opportunities.

    Queries fin_arbitrage_work for price discrepancies > 0.5%.
    """

    THRESHOLD_PCT = 0.5  # Minimum arb percentage to flag

    def __init__(self, db_session: Session):
        self.db = db_session

    def detect(self) -> list[dict]:
        """Scan for arb opportunities across exchanges.

        Returns:
            List of detected signal dicts.
        """
        # Find assets with prices on multiple exchanges where spread > threshold
        result = self.db.execute(
            text("""
                SELECT
                    a.asset_id,
                    a.pair_key,
                    a.exchange AS exchange_a,
                    a.price AS price_a,
                    b.exchange AS exchange_b,
                    b.price AS price_b,
                    ABS(a.price - b.price) / LEAST(a.price, b.price) * 100 AS arb_pct
                FROM fin_arbitrage_work a
                JOIN fin_arbitrage_work b
                    ON a.asset_id = b.asset_id
                    AND a.pair_key = b.pair_key
                    AND a.exchange < b.exchange
                WHERE a.observed_at > NOW() - INTERVAL '5 minutes'
                    AND b.observed_at > NOW() - INTERVAL '5 minutes'
                    AND ABS(a.price - b.price) / LEAST(a.price, b.price) * 100 > :threshold
            """),
            {"threshold": self.THRESHOLD_PCT},
        )

        signals = []
        for row in result.fetchall():
            signal = {
                "asset_id": row[0],
                "signal_type": "CROSS_EXCHANGE_ARB",
                "signal_subtype": f"{row[2]}_vs_{row[4]}",
                "direction": "LONG" if row[3] < row[5] else "SHORT",
                "strength": min(row[6] / 5.0, 1.0),  # Normalize to 0-1
                "confidence_tier": "HIGH" if row[6] > 2.0 else "MEDIUM" if row[6] > 1.0 else "LOW",
                "trigger_price": float(row[3]),
                "target_price": float(row[5]),
                "ev_estimate": float(row[6]),
                "derivation": {
                    "exchange_a": row[2],
                    "price_a": float(row[3]),
                    "exchange_b": row[4],
                    "price_b": float(row[5]),
                    "arb_pct": float(row[6]),
                },
            }
            signals.append(signal)

        logger.info("arb_detector.complete", signals_found=len(signals))
        return signals


class VolumeAnomalyDetector:
    """Detect unusual volume spikes (current vs 20-day average)."""

    VOLUME_MULTIPLIER = 2.0  # Flag when volume > 2x the 20-day avg

    def __init__(self, db_session: Session):
        self.db = db_session

    def detect(self) -> list[dict]:
        """Scan for volume anomalies.

        Compares today's volume against the 20-day average from fin_candles.
        """
        result = self.db.execute(
            text("""
                WITH recent_volume AS (
                    SELECT
                        asset_id,
                        SUM(volume) AS today_volume
                    FROM fin_candles
                    WHERE timestamp > CURRENT_DATE
                        AND interval = '1d'
                    GROUP BY asset_id
                ),
                avg_volume AS (
                    SELECT
                        asset_id,
                        AVG(volume) AS avg_20d_volume
                    FROM fin_candles
                    WHERE timestamp > CURRENT_DATE - INTERVAL '20 days'
                        AND timestamp <= CURRENT_DATE
                        AND interval = '1d'
                    GROUP BY asset_id
                    HAVING AVG(volume) > 0
                )
                SELECT
                    rv.asset_id,
                    rv.today_volume,
                    av.avg_20d_volume,
                    rv.today_volume / av.avg_20d_volume AS volume_ratio
                FROM recent_volume rv
                JOIN avg_volume av ON rv.asset_id = av.asset_id
                WHERE rv.today_volume / av.avg_20d_volume > :threshold
            """),
            {"threshold": self.VOLUME_MULTIPLIER},
        )

        signals = []
        for row in result.fetchall():
            ratio = float(row[3])
            signal = {
                "asset_id": row[0],
                "signal_type": "VOLUME_ANOMALY",
                "signal_subtype": "high_volume",
                "direction": "NEUTRAL",
                "strength": min(ratio / 10.0, 1.0),
                "confidence_tier": "HIGH" if ratio > 5.0 else "MEDIUM" if ratio > 3.0 else "LOW",
                "ev_estimate": None,
                "derivation": {
                    "today_volume": float(row[1]),
                    "avg_20d_volume": float(row[2]),
                    "volume_ratio": ratio,
                },
            }
            signals.append(signal)

        logger.info("volume_detector.complete", signals_found=len(signals))
        return signals


class SentimentDivergenceDetector:
    """Detect sentiment-price divergence (bullish sentiment + falling price, or vice versa)."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def detect(self) -> list[dict]:
        """Scan for sentiment-price divergence.

        Compares recent sentiment direction vs price movement.
        """
        result = self.db.execute(
            text("""
                WITH recent_sentiment AS (
                    SELECT
                        asset_id,
                        weighted_sentiment,
                        observed_at
                    FROM fin_sentiment_snapshots
                    WHERE asset_id IS NOT NULL
                        AND observed_at > NOW() - INTERVAL '2 hours'
                    ORDER BY observed_at DESC
                ),
                recent_price AS (
                    SELECT
                        s.asset_id,
                        s.change_pct
                    FROM fin_sessions s
                    WHERE s.session_date >= CURRENT_DATE - 1
                        AND s.change_pct IS NOT NULL
                )
                SELECT DISTINCT ON (rs.asset_id)
                    rs.asset_id,
                    rs.weighted_sentiment,
                    rp.change_pct
                FROM recent_sentiment rs
                JOIN recent_price rp ON rs.asset_id = rp.asset_id
                WHERE (rs.weighted_sentiment > 0.3 AND rp.change_pct < -2.0)
                   OR (rs.weighted_sentiment < -0.3 AND rp.change_pct > 2.0)
                ORDER BY rs.asset_id, rs.observed_at DESC
            """)
        )

        signals = []
        for row in result.fetchall():
            sentiment = float(row[1])
            price_change = float(row[2])

            # Bullish sentiment + falling price → potential buy
            # Bearish sentiment + rising price → potential sell
            direction = "LONG" if sentiment > 0 else "SHORT"

            signal = {
                "asset_id": row[0],
                "signal_type": "SENTIMENT_DIVERGENCE",
                "signal_subtype": "sentiment_vs_price",
                "direction": direction,
                "strength": min(abs(sentiment) * abs(price_change) / 10.0, 1.0),
                "confidence_tier": "MEDIUM",
                "ev_estimate": None,
                "derivation": {
                    "weighted_sentiment": sentiment,
                    "price_change_pct": price_change,
                    "interpretation": (
                        "bullish sentiment despite falling price"
                        if sentiment > 0
                        else "bearish sentiment despite rising price"
                    ),
                },
            }
            signals.append(signal)

        logger.info("sentiment_detector.complete", signals_found=len(signals))
        return signals


class SignalPipeline:
    """Orchestrates all signal detectors."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.detectors = [
            ArbitrageDetector(db_session),
            VolumeAnomalyDetector(db_session),
            SentimentDivergenceDetector(db_session),
        ]

    def run(self) -> dict:
        """Run all detectors and persist signals."""
        results = {
            "assets_scanned": 0,
            "signals_created": 0,
            "arb_detected": 0,
            "volume_detected": 0,
            "sentiment_detected": 0,
        }

        all_signals = []
        for detector in self.detectors:
            try:
                signals = detector.detect()
                all_signals.extend(signals)
            except Exception as e:
                logger.error(
                    "signal_pipeline.detector_error",
                    detector=detector.__class__.__name__,
                    error=str(e),
                )

        # Persist signals
        now = datetime.now(timezone.utc)
        asset_ids = set()

        for signal in all_signals:
            asset_ids.add(signal["asset_id"])
            self._persist_signal(signal, now)

            # Count by type
            if signal["signal_type"] == "CROSS_EXCHANGE_ARB":
                results["arb_detected"] += 1
            elif signal["signal_type"] == "VOLUME_ANOMALY":
                results["volume_detected"] += 1
            elif signal["signal_type"] == "SENTIMENT_DIVERGENCE":
                results["sentiment_detected"] += 1

        self.db.commit()

        results["assets_scanned"] = len(asset_ids)
        results["signals_created"] = len(all_signals)

        logger.info("signal_pipeline.complete", **results)
        return results

    def _persist_signal(self, signal: dict, detected_at: datetime) -> None:
        """Persist a single alpha signal."""
        # Get asset_class_id
        result = self.db.execute(
            text("SELECT asset_class_id FROM fin_assets WHERE id = :id"),
            {"id": signal["asset_id"]},
        )
        row = result.fetchone()
        asset_class_id = row[0] if row else None

        self.db.execute(
            text("""
                INSERT INTO fin_alpha_signals
                    (asset_id, asset_class_id, signal_type, signal_subtype,
                     direction, strength, confidence_tier, ev_estimate,
                     trigger_price, target_price, detected_at, outcome, derivation)
                VALUES
                    (:asset_id, :asset_class_id, :signal_type, :signal_subtype,
                     :direction, :strength, :confidence_tier, :ev_estimate,
                     :trigger_price, :target_price, :detected_at, 'PENDING',
                     :derivation)
            """),
            {
                "asset_id": signal["asset_id"],
                "asset_class_id": asset_class_id,
                "signal_type": signal["signal_type"],
                "signal_subtype": signal.get("signal_subtype"),
                "direction": signal["direction"],
                "strength": signal["strength"],
                "confidence_tier": signal["confidence_tier"],
                "ev_estimate": signal.get("ev_estimate"),
                "trigger_price": signal.get("trigger_price"),
                "target_price": signal.get("target_price"),
                "detected_at": detected_at,
                "derivation": str(signal.get("derivation", {})),
            },
        )
