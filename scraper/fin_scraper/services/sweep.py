"""Daily sweep functions — cleanup, backfill, reconciliation.

Functions for the daily maintenance sweep task.
"""

from datetime import datetime, timezone, timedelta

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)


def close_past_sessions(db: Session) -> int:
    """Close sessions that are past their session_date and still marked as non-closed.

    Returns:
        Number of sessions closed.
    """
    result = db.execute(
        text("""
            UPDATE fin_sessions
            SET status = 'closed', updated_at = NOW()
            WHERE status != 'closed'
                AND session_date < CURRENT_DATE
            RETURNING id
        """)
    )
    rows = result.fetchall()
    db.commit()
    count = len(rows)
    if count:
        logger.info("sweep.sessions_closed", count=count)
    return count


def prune_arb_work(db: Session, max_age_hours: int = 24) -> int:
    """Remove stale arbitrage work entries older than max_age_hours.

    Returns:
        Number of entries pruned.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    result = db.execute(
        text("""
            DELETE FROM fin_arbitrage_work
            WHERE observed_at < :cutoff
            RETURNING asset_id
        """),
        {"cutoff": cutoff},
    )
    rows = result.fetchall()
    db.commit()
    count = len(rows)
    if count:
        logger.info("sweep.arb_pruned", count=count)
    return count


def resolve_signal_outcomes(db: Session) -> int:
    """Resolve pending signals that have expired.

    Marks signals past their expires_at as EXPIRED.

    Returns:
        Number of signals resolved.
    """
    result = db.execute(
        text("""
            UPDATE fin_alpha_signals
            SET outcome = 'EXPIRED',
                resolved_at = NOW(),
                updated_at = NOW()
            WHERE outcome = 'PENDING'
                AND expires_at IS NOT NULL
                AND expires_at < NOW()
            RETURNING id
        """)
    )
    rows = result.fetchall()
    db.commit()
    count = len(rows)
    if count:
        logger.info("sweep.signals_expired", count=count)
    return count


def update_asset_metadata(db: Session) -> int:
    """Update asset market_cap from latest fundamentals.

    Returns:
        Number of assets updated.
    """
    result = db.execute(
        text("""
            UPDATE fin_assets a
            SET market_cap = f.market_cap,
                updated_at = NOW()
            FROM fin_asset_fundamentals f
            WHERE f.asset_id = a.id
                AND f.snapshot_date = (
                    SELECT MAX(snapshot_date)
                    FROM fin_asset_fundamentals
                    WHERE asset_id = a.id
                )
                AND f.market_cap IS NOT NULL
                AND (a.market_cap IS NULL OR a.market_cap != f.market_cap)
            RETURNING a.id
        """)
    )
    rows = result.fetchall()
    db.commit()
    count = len(rows)
    if count:
        logger.info("sweep.assets_metadata_updated", count=count)
    return count


def detect_conflicts(db: Session) -> int:
    """Detect duplicate or stale data and log as data conflicts.

    Currently checks for:
    - Stale prices (assets with no candles in 48+ hours that should have them)

    Returns:
        Number of conflicts detected.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=48)

    # Find active assets with no recent candles
    result = db.execute(
        text("""
            SELECT a.id, a.ticker, a.asset_class_id
            FROM fin_assets a
            WHERE a.is_active = true
                AND (a.last_price_at IS NULL OR a.last_price_at < :cutoff)
        """),
        {"cutoff": cutoff},
    )
    stale_assets = result.fetchall()

    created = 0
    for asset_id, ticker, asset_class_id in stale_assets:
        db.execute(
            text("""
                INSERT INTO fin_data_conflicts
                    (asset_class_id, asset_id, conflict_type, source, description)
                VALUES
                    (:asset_class_id, :asset_id, 'stale_data', 'sweep',
                     :description)
            """),
            {
                "asset_class_id": asset_class_id,
                "asset_id": asset_id,
                "description": f"No price data for {ticker} in 48+ hours",
            },
        )
        created += 1

    if created:
        db.commit()
        logger.info("sweep.conflicts_detected", count=created)
    return created
