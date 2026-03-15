"""Macro economic data ingestion — FRED series.

Tasks:
    ingest_macro_data  — Fetch FRED economic indicators (daily at 06:30 UTC)
"""

import structlog
from celery import shared_task

from fin_scraper.db import get_db_session
from fin_scraper.services.run_manager import create_run, complete_run, fail_run

logger = structlog.get_logger(__name__)


@shared_task(name="fin_scraper.jobs.macro_tasks.ingest_macro_data")
def ingest_macro_data() -> dict:
    """Ingest macroeconomic indicators from FRED.

    Tracked series: FEDFUNDS, CPIAUCSL, GDP, UNRATE, T10Y2Y, VIXCLS.
    """
    with get_db_session() as db:
        run = create_run(db, "macro_ingest", requested_by="celery_beat")
        try:
            logger.info("macro_ingest.start")

            from fin_scraper.config import get_settings
            from fin_scraper.clients.fred_client import FredClient
            from sqlalchemy import text

            settings = get_settings()
            if not settings.fred_api_key:
                logger.warning("macro_ingest.no_fred_key")
                complete_run(db, run, summary="no API key")
                return {"observations_fetched": 0, "observations_created": 0}

            client = FredClient(api_key=settings.fred_api_key)
            observations = client.get_all_tracked_series(days_back=30)
            client.close()

            results = {
                "observations_fetched": len(observations),
                "observations_created": 0,
            }

            for obs in observations:
                result = db.execute(
                    text("""
                        INSERT INTO fin_economic_indicators
                            (series_id, series_name, category, value,
                             observation_date, source, raw_data)
                        VALUES
                            (:series_id, :series_name, :category, :value,
                             :observation_date, :source, :raw_data)
                        ON CONFLICT (series_id, observation_date) DO UPDATE SET
                            value = EXCLUDED.value,
                            raw_data = EXCLUDED.raw_data
                        RETURNING id
                    """),
                    {
                        "series_id": obs["series_id"],
                        "series_name": obs["series_name"],
                        "category": obs["category"],
                        "value": obs["value"],
                        "observation_date": obs["observation_date"],
                        "source": obs["source"],
                        "raw_data": str(obs.get("raw_data", {})),
                    },
                )
                if result.fetchone() is not None:
                    results["observations_created"] += 1

            db.commit()
            complete_run(db, run, summary=str(results))
            logger.info("macro_ingest.complete", **results)
            return results

        except Exception as e:
            fail_run(db, run, error=str(e))
            logger.error("macro_ingest.failed", error=str(e))
            raise
