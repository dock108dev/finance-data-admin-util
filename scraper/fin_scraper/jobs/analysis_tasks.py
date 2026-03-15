"""Market analysis generation tasks — equivalent to flow generation tasks.

Tasks:
    generate_daily_analyses   — AI market narrative generation for all sessions
    generate_asset_analysis   — Single asset analysis (manual trigger)
"""

from datetime import date, timedelta

import structlog
from celery import shared_task
from sqlalchemy import text

from fin_scraper.db import get_db_session
from fin_scraper.services.run_manager import create_run, complete_run, fail_run

logger = structlog.get_logger(__name__)


@shared_task(name="fin_scraper.jobs.analysis_tasks.generate_daily_analyses")
def generate_daily_analyses() -> dict:
    """Generate AI market narratives for yesterday's sessions.

    Equivalent to daily game flow generation (4:30 AM EST).
    Queries sessions with status='closed' and no existing analysis,
    then triggers the pipeline for each via the API.
    """
    with get_db_session() as db:
        run = create_run(db, "analysis_generation", requested_by="celery_beat")
        try:
            logger.info("analysis_generation.start")

            yesterday = date.today() - timedelta(days=1)

            # Find closed sessions that don't have an analysis yet
            result = db.execute(
                text("""
                    SELECT s.id, s.asset_id, s.session_date
                    FROM fin_sessions s
                    LEFT JOIN fin_market_analyses a
                        ON a.asset_id = s.asset_id
                        AND a.analysis_date = s.session_date
                    WHERE s.status = 'closed'
                      AND s.session_date = :yesterday
                      AND a.id IS NULL
                    ORDER BY s.asset_id
                """),
                {"yesterday": yesterday},
            )
            eligible_sessions = result.fetchall()

            results = {
                "sessions_analyzed": 0,
                "analyses_created": 0,
                "timelines_created": 0,
                "errors": 0,
                "session_date": str(yesterday),
            }

            for session_row in eligible_sessions:
                asset_id = session_row[1]
                session_date = session_row[2]

                try:
                    logger.info(
                        "analysis_generation.processing",
                        asset_id=asset_id,
                        session_date=str(session_date),
                    )

                    # Call the pipeline via the API internal endpoint
                    import httpx
                    import os

                    api_url = os.getenv("API_URL", "http://api:8000")
                    api_key = os.getenv("API_KEY", "dev-key-do-not-use-in-production")

                    response = httpx.post(
                        f"{api_url}/api/admin/pipeline/{asset_id}/run",
                        params={"session_date": str(session_date), "sync": "true"},
                        headers={"X-API-Key": api_key},
                        timeout=120.0,
                    )

                    if response.status_code == 200:
                        pipeline_result = response.json()
                        if pipeline_result.get("status") == "completed":
                            results["analyses_created"] += 1
                            if pipeline_result.get("timeline_id"):
                                results["timelines_created"] += 1
                        else:
                            results["errors"] += 1
                    else:
                        logger.error(
                            "analysis_generation.api_error",
                            asset_id=asset_id,
                            status_code=response.status_code,
                        )
                        results["errors"] += 1

                    results["sessions_analyzed"] += 1

                except Exception as e:
                    logger.error(
                        "analysis_generation.asset_error",
                        asset_id=asset_id,
                        error=str(e),
                    )
                    results["errors"] += 1

            complete_run(db, run, summary=str(results))
            logger.info("analysis_generation.complete", **results)
            return results

        except Exception as e:
            fail_run(db, run, error=str(e))
            raise


@shared_task(name="fin_scraper.jobs.analysis_tasks.generate_asset_analysis")
def generate_asset_analysis(asset_id: int, session_date: str) -> dict:
    """Generate analysis for a single asset session — manual trigger.

    Equivalent to trigger_flow_for_game in sports-data-admin.
    """
    with get_db_session() as db:
        run = create_run(db, "analysis_generation", requested_by="admin_manual")
        try:
            logger.info(
                "analysis_generation.single",
                asset_id=asset_id,
                session_date=session_date,
            )

            import httpx
            import os

            api_url = os.getenv("API_URL", "http://api:8000")
            api_key = os.getenv("API_KEY", "dev-key-do-not-use-in-production")

            response = httpx.post(
                f"{api_url}/api/admin/pipeline/{asset_id}/run",
                params={"session_date": session_date, "sync": "true"},
                headers={"X-API-Key": api_key},
                timeout=120.0,
            )

            if response.status_code == 200:
                results = response.json()
            else:
                results = {
                    "asset_id": asset_id,
                    "session_date": session_date,
                    "status": "failed",
                    "error": f"API returned {response.status_code}",
                }

            complete_run(db, run, summary=str(results))
            return results

        except Exception as e:
            fail_run(db, run, error=str(e))
            raise
