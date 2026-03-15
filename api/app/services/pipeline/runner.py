"""Pipeline execution runner — creates JobRun records and runs the orchestrator.

Called by both the admin API endpoint and the Celery analysis task.
Equivalent to sports-data-admin's pipeline executor.
"""

from datetime import date, datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pipeline import PipelineStage
from app.services.pipeline.orchestrator import AnalysisPipelineOrchestrator, PipelineResult

logger = structlog.get_logger(__name__)

# ── SQL for pipeline stage tracking ─────────────────────────────────────────

_CREATE_JOB_RUN = text("""
    INSERT INTO fin_job_runs (phase, asset_classes, status, started_at, created_at)
    VALUES (:phase, :asset_classes, 'running', :started_at, :started_at)
    RETURNING id
""")

_COMPLETE_JOB_RUN = text("""
    UPDATE fin_job_runs
    SET status = 'completed',
        finished_at = :finished_at,
        duration_seconds = :duration_seconds,
        summary_data = :summary_data
    WHERE id = :job_run_id
""")

_FAIL_JOB_RUN = text("""
    UPDATE fin_job_runs
    SET status = 'failed',
        finished_at = :finished_at,
        duration_seconds = :duration_seconds,
        error_summary = :error_summary
    WHERE id = :job_run_id
""")

_INSERT_STAGE_RUN = text("""
    INSERT INTO fin_pipeline_stage_runs
        (job_run_id, stage, status, started_at, finished_at, duration_ms, output_json, error_details)
    VALUES
        (:job_run_id, :stage, :status, :started_at, :finished_at, :duration_ms,
         :output_json, :error_details)
""")


async def run_pipeline_for_asset(
    db: AsyncSession,
    asset_id: int,
    session_date: date | None = None,
) -> dict:
    """Run the full 8-stage analysis pipeline for an asset.

    Creates a JobRun record, executes all stages via the orchestrator,
    records per-stage results in fin_pipeline_stage_runs, and updates
    the JobRun with final status.

    Returns:
        dict with job_run_id, stage_results, overall status, and timing.
    """
    session_date = session_date or date.today()
    started_at = datetime.now(timezone.utc)

    # Create the parent JobRun
    job_run_id = await _create_job_run(db, asset_id, started_at)

    # Run the pipeline
    orchestrator = AnalysisPipelineOrchestrator(db)
    results = await orchestrator.run(asset_id=asset_id, session_date=session_date)

    finished_at = datetime.now(timezone.utc)
    duration = (finished_at - started_at).total_seconds()

    # Record per-stage results
    if job_run_id > 0:
        for result in results:
            await _record_stage_run(db, job_run_id, result, started_at)

    # Determine overall success
    all_success = all(r.success for r in results)
    ran_all = len(results) == len(PipelineStage)

    if all_success and ran_all:
        await _complete_job_run(db, job_run_id, finished_at, duration, results)
        status = "completed"
    else:
        failed_stage = next((r for r in results if not r.success), None)
        error_msg = failed_stage.error if failed_stage else "incomplete"
        await _fail_job_run(db, job_run_id, finished_at, duration, error_msg)
        status = "failed"

    logger.info(
        "pipeline.run_complete",
        asset_id=asset_id,
        session_date=str(session_date),
        job_run_id=job_run_id,
        status=status,
        stages_run=len(results),
        duration_seconds=round(duration, 2),
    )

    return {
        "job_run_id": job_run_id,
        "asset_id": asset_id,
        "session_date": str(session_date),
        "status": status,
        "stages_run": len(results),
        "duration_seconds": round(duration, 2),
        "stage_results": [
            {
                "stage": r.stage.value,
                "success": r.success,
                "duration_ms": round(r.duration_ms, 1),
                "error": r.error,
            }
            for r in results
        ],
    }


async def _create_job_run(
    db: AsyncSession, asset_id: int, started_at: datetime
) -> int:
    """Create a JobRun record, return its ID."""
    try:
        import json
        result = await db.execute(
            _CREATE_JOB_RUN,
            {
                "phase": f"analysis_pipeline_asset_{asset_id}",
                "asset_classes": json.dumps(["ALL"]),
                "started_at": started_at,
            },
        )
        row = result.fetchone()
        await db.flush()
        return row[0] if row else -1
    except Exception as e:
        logger.warning("pipeline.job_run_create_failed", error=str(e))
        return -1


async def _record_stage_run(
    db: AsyncSession,
    job_run_id: int,
    result: PipelineResult,
    pipeline_start: datetime,
) -> None:
    """Insert a stage run record."""
    try:
        import json
        now = datetime.now(timezone.utc)
        stage_started = datetime.now(timezone.utc)  # approximate

        await db.execute(
            _INSERT_STAGE_RUN,
            {
                "job_run_id": job_run_id,
                "stage": result.stage.value,
                "status": "completed" if result.success else "failed",
                "started_at": stage_started,
                "finished_at": now,
                "duration_ms": round(result.duration_ms, 1),
                "output_json": json.dumps(result.data) if result.data else None,
                "error_details": result.error,
            },
        )
    except Exception as e:
        logger.warning(
            "pipeline.stage_run_record_failed",
            stage=result.stage.value,
            error=str(e),
        )


async def _complete_job_run(
    db: AsyncSession,
    job_run_id: int,
    finished_at: datetime,
    duration: float,
    results: list[PipelineResult],
) -> None:
    """Mark a JobRun as completed."""
    if job_run_id <= 0:
        return
    try:
        import json
        summary = {
            "stages_completed": len(results),
            "total_duration_ms": sum(r.duration_ms for r in results),
        }
        await db.execute(
            _COMPLETE_JOB_RUN,
            {
                "job_run_id": job_run_id,
                "finished_at": finished_at,
                "duration_seconds": round(duration, 2),
                "summary_data": json.dumps(summary),
            },
        )
    except Exception as e:
        logger.warning("pipeline.job_run_complete_failed", error=str(e))


async def _fail_job_run(
    db: AsyncSession,
    job_run_id: int,
    finished_at: datetime,
    duration: float,
    error_summary: str,
) -> None:
    """Mark a JobRun as failed."""
    if job_run_id <= 0:
        return
    try:
        await db.execute(
            _FAIL_JOB_RUN,
            {
                "job_run_id": job_run_id,
                "finished_at": finished_at,
                "duration_seconds": round(duration, 2),
                "error_summary": error_summary,
            },
        )
    except Exception as e:
        logger.warning("pipeline.job_run_fail_update_failed", error=str(e))
