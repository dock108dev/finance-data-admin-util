"""Daily sweep tasks — cleanup, backfill, reconciliation.

Tasks:
    run_daily_sweep  — Comprehensive daily maintenance
"""

import structlog
from celery import shared_task

from fin_scraper.db import get_db_session
from fin_scraper.services.run_manager import create_run, complete_run, fail_run

logger = structlog.get_logger(__name__)


@shared_task(name="fin_scraper.jobs.sweep_tasks.run_daily_sweep")
def run_daily_sweep() -> dict:
    """Daily maintenance sweep.

    Steps:
    1. Close past sessions (scheduled → closed)
    2. Prune expired arbitrage work entries
    3. Resolve expired signal outcomes
    4. Update asset metadata from latest fundamentals
    5. Detect and log data conflicts (stale prices, etc.)
    """
    with get_db_session() as db:
        run = create_run(db, "daily_sweep", requested_by="celery_beat")
        try:
            logger.info("daily_sweep.start")

            from fin_scraper.services.sweep import (
                close_past_sessions,
                prune_arb_work,
                resolve_signal_outcomes,
                update_asset_metadata,
                detect_conflicts,
            )

            results = {
                "sessions_closed": close_past_sessions(db),
                "arb_entries_pruned": prune_arb_work(db),
                "signals_resolved": resolve_signal_outcomes(db),
                "assets_metadata_updated": update_asset_metadata(db),
                "conflicts_detected": detect_conflicts(db),
            }

            complete_run(db, run, summary=str(results))
            logger.info("daily_sweep.complete", **results)
            return results

        except Exception as e:
            fail_run(db, run, error=str(e))
            logger.error("daily_sweep.failed", error=str(e))
            raise
