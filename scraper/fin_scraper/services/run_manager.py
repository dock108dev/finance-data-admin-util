"""Run execution tracking — equivalent to sports-data-admin's run_manager.py.

Creates and updates ScrapeRun records for tracking task execution.
"""

from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)

# Import the model path — will be resolved when DB models are shared
# For now, use raw SQL or a lightweight dataclass
_RUN_INSERT = """
INSERT INTO fin_scrape_runs (scraper_type, status, requested_by, started_at)
VALUES (:scraper_type, 'running', :requested_by, :started_at)
RETURNING id
"""

_RUN_COMPLETE = """
UPDATE fin_scrape_runs
SET status = 'completed', finished_at = :finished_at, summary = :summary
WHERE id = :run_id
"""

_RUN_FAIL = """
UPDATE fin_scrape_runs
SET status = 'failed', finished_at = :finished_at, error_details = :error
WHERE id = :run_id
"""


class RunRecord:
    """Lightweight run record."""
    def __init__(self, id: int, scraper_type: str):
        self.id = id
        self.scraper_type = scraper_type


def create_run(db: Session, scraper_type: str, requested_by: str = "celery_beat") -> RunRecord:
    """Create a new scrape run record."""
    try:
        from sqlalchemy import text
        result = db.execute(
            text(_RUN_INSERT),
            {
                "scraper_type": scraper_type,
                "requested_by": requested_by,
                "started_at": datetime.now(timezone.utc),
            },
        )
        run_id = result.fetchone()[0]
        db.commit()
        logger.info("run.created", run_id=run_id, scraper_type=scraper_type)
        return RunRecord(id=run_id, scraper_type=scraper_type)
    except Exception as e:
        logger.warning("run.create_failed", error=str(e), scraper_type=scraper_type)
        # Return a dummy run so tasks can still execute
        return RunRecord(id=-1, scraper_type=scraper_type)


def complete_run(db: Session, run: RunRecord, summary: str = "") -> None:
    """Mark a run as completed."""
    if run.id == -1:
        return
    try:
        from sqlalchemy import text
        db.execute(
            text(_RUN_COMPLETE),
            {
                "run_id": run.id,
                "finished_at": datetime.now(timezone.utc),
                "summary": summary,
            },
        )
        db.commit()
        logger.info("run.completed", run_id=run.id)
    except Exception as e:
        logger.warning("run.complete_failed", error=str(e), run_id=run.id)


def fail_run(db: Session, run: RunRecord, error: str = "") -> None:
    """Mark a run as failed."""
    if run.id == -1:
        return
    try:
        from sqlalchemy import text
        db.execute(
            text(_RUN_FAIL),
            {
                "run_id": run.id,
                "finished_at": datetime.now(timezone.utc),
                "error": error,
            },
        )
        db.commit()
        logger.error("run.failed", run_id=run.id, error=error)
    except Exception as e:
        logger.warning("run.fail_update_failed", error=str(e), run_id=run.id)
