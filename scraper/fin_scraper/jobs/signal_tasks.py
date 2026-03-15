"""Signal detection tasks — detect alpha opportunities.

Tasks:
    run_signal_pipeline  — Run all signal detectors (arb, volume, sentiment)
"""

import structlog
from celery import shared_task

from fin_scraper.db import get_db_session
from fin_scraper.services.run_manager import create_run, complete_run, fail_run

logger = structlog.get_logger(__name__)


@shared_task(name="fin_scraper.jobs.signal_tasks.run_signal_pipeline")
def run_signal_pipeline(
    asset_class: str | None = None,
    asset_id: int | None = None,
) -> dict:
    """Run the signal detection pipeline — find alpha opportunities.

    Detects:
    - Cross-exchange arbitrage (from exchange_sync data)
    - Volume anomalies (current vol vs 20-day avg)
    - Sentiment-price divergence
    """
    with get_db_session() as db:
        run = create_run(db, "signal_pipeline", requested_by="celery_beat")
        try:
            logger.info(
                "signal_pipeline.start",
                asset_class=asset_class,
                asset_id=asset_id,
            )

            from fin_scraper.signals.detector import SignalPipeline

            pipeline = SignalPipeline(db)
            results = pipeline.run()

            complete_run(db, run, summary=str(results))
            logger.info("signal_pipeline.complete", **results)
            return results

        except Exception as e:
            fail_run(db, run, error=str(e))
            logger.error("signal_pipeline.failed", error=str(e))
            raise
