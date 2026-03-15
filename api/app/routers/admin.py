"""Admin endpoints — task control, pipeline management, data inspection.

Equivalent to sports-data-admin's admin routes.

POST /api/admin/tasks/trigger       — Trigger a scraper task
GET  /api/admin/tasks/registry      — List available tasks
GET  /api/admin/tasks/runs          — List recent scrape runs
GET  /api/admin/pipeline/{id}/run   — Run analysis pipeline for asset
GET  /api/admin/pipeline/jobs       — List pipeline job runs
GET  /api/admin/data/conflicts      — List data conflicts
POST /api/admin/exchange/sync       — Trigger exchange price sync
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_client import get_celery_app
from app.db.session import get_db
from app.db.scraper import ScrapeRun, JobRun, DataConflict, PipelineStageRun
from app.dependencies.auth import require_api_key
from app.services.pipeline.runner import run_pipeline_for_asset

import logging as _logging

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_api_key)])


# ── Request / Response Models ────────────────────────────────────────────────

class TriggerTaskRequest(BaseModel):
    task_name: str
    asset_class: str | None = None
    params: dict | None = None


class TriggerTaskResponse(BaseModel):
    job_id: str
    task_name: str
    status: str


class TaskRegistryEntry(BaseModel):
    name: str
    description: str
    params: list[str]
    asset_classes: list[str]


class ScrapeRunResponse(BaseModel):
    id: int
    scraper_type: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    assets_processed: int | None = None
    records_created: int | None = None
    error_details: str | None = None

    model_config = {"from_attributes": True}


class JobRunResponse(BaseModel):
    id: int
    phase: str
    asset_classes: list[str] | None = None
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    error_summary: str | None = None
    summary_data: dict | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class DataConflictResponse(BaseModel):
    id: int
    conflict_type: str
    source: str | None = None
    description: str | None = None
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Task Registry ───────────────────────────────────────────────────────────

# Maps registry name → full Celery task path
TASK_NAME_MAP: dict[str, str] = {
    "ingest_daily_prices": "fin_scraper.jobs.price_tasks.ingest_daily_prices",
    "ingest_intraday_prices": "fin_scraper.jobs.price_tasks.ingest_intraday_prices",
    "sync_exchange_prices": "fin_scraper.jobs.price_tasks.sync_exchange_prices",
    "ingest_fundamentals": "fin_scraper.jobs.price_tasks.ingest_fundamentals",
    "collect_social_sentiment": "fin_scraper.jobs.social_tasks.collect_social_sentiment",
    "ingest_news": "fin_scraper.jobs.social_tasks.ingest_news",
    "run_signal_pipeline": "fin_scraper.jobs.signal_tasks.run_signal_pipeline",
    "sync_onchain_data": "fin_scraper.jobs.onchain_tasks.sync_onchain_data",
    "generate_market_analysis": "fin_scraper.jobs.analysis_tasks.generate_daily_analyses",
    "run_daily_sweep": "fin_scraper.jobs.sweep_tasks.run_daily_sweep",
    "ingest_macro_data": "fin_scraper.jobs.macro_tasks.ingest_macro_data",
}

TASK_REGISTRY: list[TaskRegistryEntry] = [
    TaskRegistryEntry(
        name="ingest_daily_prices",
        description="Ingest end-of-day OHLCV data for all assets",
        params=["date"],
        asset_classes=["STOCKS", "CRYPTO"],
    ),
    TaskRegistryEntry(
        name="ingest_intraday_prices",
        description="Ingest intraday candle data (5m intervals)",
        params=[],
        asset_classes=["STOCKS", "CRYPTO"],
    ),
    TaskRegistryEntry(
        name="sync_exchange_prices",
        description="Sync cross-exchange prices for arbitrage detection",
        params=["asset_class"],
        asset_classes=["CRYPTO"],
    ),
    TaskRegistryEntry(
        name="collect_social_sentiment",
        description="Scrape Twitter/Reddit for cashtag mentions and sentiment",
        params=["asset_class", "hours_back"],
        asset_classes=["STOCKS", "CRYPTO"],
    ),
    TaskRegistryEntry(
        name="ingest_news",
        description="Ingest financial news articles and headlines",
        params=["hours_back"],
        asset_classes=["STOCKS", "CRYPTO"],
    ),
    TaskRegistryEntry(
        name="sync_onchain_data",
        description="Sync on-chain metrics (whale wallets, gas, DEX volume)",
        params=["chain"],
        asset_classes=["CRYPTO"],
    ),
    TaskRegistryEntry(
        name="run_signal_pipeline",
        description="Run technical + fundamental signal detection",
        params=["asset_class", "asset_id"],
        asset_classes=["STOCKS", "CRYPTO"],
    ),
    TaskRegistryEntry(
        name="generate_market_analysis",
        description="Generate AI market narrative for a session",
        params=["asset_id", "session_date"],
        asset_classes=["STOCKS", "CRYPTO"],
    ),
    TaskRegistryEntry(
        name="run_daily_sweep",
        description="Daily cleanup: backfill gaps, reconcile data, prune stale records",
        params=[],
        asset_classes=["STOCKS", "CRYPTO"],
    ),
    TaskRegistryEntry(
        name="ingest_fundamentals",
        description="Fetch fundamental data (P/E, EPS, TVL, supply)",
        params=["asset_class"],
        asset_classes=["STOCKS", "CRYPTO"],
    ),
    TaskRegistryEntry(
        name="ingest_macro_data",
        description="Ingest macroeconomic indicators from FRED",
        params=[],
        asset_classes=["STOCKS", "CRYPTO"],
    ),
]


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/tasks/trigger", response_model=TriggerTaskResponse)
async def trigger_task(request: TriggerTaskRequest):
    """Manually trigger a scraper/pipeline task."""
    valid_names = {t.name for t in TASK_REGISTRY}
    if request.task_name not in valid_names:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task: {request.task_name}. "
                   f"Valid tasks: {sorted(valid_names)}"
        )

    celery_task_path = TASK_NAME_MAP[request.task_name]
    kwargs = request.params or {}
    if request.asset_class:
        kwargs.setdefault("asset_class", request.asset_class)

    celery = get_celery_app()
    result = celery.send_task(celery_task_path, kwargs=kwargs, queue="fin-scraper")
    logger.info("Dispatched Celery task %s → %s (id=%s)", request.task_name, celery_task_path, result.id)

    return TriggerTaskResponse(
        job_id=result.id,
        task_name=request.task_name,
        status="queued",
    )


@router.get("/tasks/registry", response_model=list[TaskRegistryEntry])
async def get_task_registry():
    """List all available scraper/pipeline tasks."""
    return TASK_REGISTRY


@router.get("/tasks/runs", response_model=list[ScrapeRunResponse])
async def list_scrape_runs(
    scraper_type: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List recent scrape run records."""
    stmt = select(ScrapeRun)

    if scraper_type:
        stmt = stmt.where(ScrapeRun.scraper_type == scraper_type)
    if status:
        stmt = stmt.where(ScrapeRun.status == status)

    stmt = stmt.order_by(ScrapeRun.started_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/pipeline/jobs", response_model=list[JobRunResponse])
async def list_pipeline_jobs(
    phase: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List pipeline job execution records."""
    stmt = select(JobRun)

    if phase:
        stmt = stmt.where(JobRun.phase == phase)
    if status:
        stmt = stmt.where(JobRun.status == status)

    stmt = stmt.order_by(JobRun.started_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/pipeline/{asset_id}/run")
async def run_pipeline(
    asset_id: int,
    session_date: str | None = Query(None),
    sync: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the full analysis pipeline for an asset.

    Args:
        sync: If True, run the pipeline synchronously and return results.
              If False (default), dispatch via Celery and return job ID.
    """
    if sync:
        # Run pipeline synchronously — used by Celery tasks and direct API calls
        from datetime import date as date_type
        sd = date_type.fromisoformat(session_date) if session_date else None
        result = await run_pipeline_for_asset(db, asset_id, sd)
        return result

    # Async: dispatch via Celery
    celery = get_celery_app()
    kwargs: dict = {"asset_id": asset_id}
    if session_date:
        kwargs["session_date"] = session_date

    result = celery.send_task(
        TASK_NAME_MAP["generate_market_analysis"],
        kwargs=kwargs,
        queue="fin-scraper",
    )
    return {
        "status": "queued",
        "job_id": result.id,
        "asset_id": asset_id,
        "session_date": session_date,
    }


@router.get("/data/conflicts", response_model=list[DataConflictResponse])
async def list_data_conflicts(
    conflict_type: str | None = Query(None),
    unresolved_only: bool = Query(True),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List data conflicts and quality issues."""
    stmt = select(DataConflict)

    if conflict_type:
        stmt = stmt.where(DataConflict.conflict_type == conflict_type)
    if unresolved_only:
        stmt = stmt.where(DataConflict.resolved_at.is_(None))

    stmt = stmt.order_by(DataConflict.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/exchange/sync")
async def trigger_exchange_sync(
    asset_class: str = Query("CRYPTO"),
):
    """Trigger an immediate exchange price sync."""
    celery = get_celery_app()
    result = celery.send_task(
        TASK_NAME_MAP["sync_exchange_prices"],
        kwargs={"asset_class": asset_class},
        queue="fin-scraper",
    )
    return {
        "status": "queued",
        "job_id": result.id,
        "asset_class": asset_class,
    }


# ── Conflict Resolution ────────────────────────────────────────────────────

class ResolveConflictRequest(BaseModel):
    resolution_notes: str


@router.post("/data/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: int,
    request: ResolveConflictRequest,
    db: AsyncSession = Depends(get_db),
):
    """Mark a data conflict as resolved."""
    from sqlalchemy import text as sql_text
    from datetime import datetime as _dt, timezone as _tz

    result = await db.execute(
        sql_text("""
            UPDATE fin_data_conflicts
            SET resolved_at = :resolved_at, resolution_notes = :notes
            WHERE id = :id AND resolved_at IS NULL
            RETURNING id
        """),
        {
            "id": conflict_id,
            "resolved_at": _dt.now(_tz.utc),
            "notes": request.resolution_notes,
        },
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Conflict not found or already resolved")

    return {"status": "resolved", "conflict_id": conflict_id}


# ── Backfill ────────────────────────────────────────────────────────────────

class BackfillRequest(BaseModel):
    task_name: str
    asset_class: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@router.post("/backfill")
async def trigger_backfill(request: BackfillRequest):
    """Trigger a historical data backfill for a date range."""
    valid_tasks = {"ingest_daily_prices", "collect_social_sentiment", "run_signal_pipeline"}
    if request.task_name not in valid_tasks:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid backfill task. Valid: {sorted(valid_tasks)}",
        )

    celery_task_path = TASK_NAME_MAP.get(request.task_name)
    if not celery_task_path:
        raise HTTPException(status_code=400, detail="Task not found in registry")

    kwargs: dict = {}
    if request.asset_class:
        kwargs["asset_class"] = request.asset_class
    if request.start_date:
        kwargs["start_date"] = request.start_date
    if request.end_date:
        kwargs["end_date"] = request.end_date
    kwargs["is_backfill"] = True

    celery = get_celery_app()
    result = celery.send_task(celery_task_path, kwargs=kwargs, queue="fin-scraper")

    return {
        "status": "queued",
        "job_id": result.id,
        "task_name": request.task_name,
        "params": kwargs,
    }


# ── Bulk Operations ────────────────────────────────────────────────────────

class BulkPipelineRequest(BaseModel):
    asset_ids: list[int]
    session_date: str | None = None


@router.post("/pipeline/bulk")
async def run_bulk_pipeline(request: BulkPipelineRequest):
    """Trigger pipeline for multiple assets at once."""
    if len(request.asset_ids) > 50:
        raise HTTPException(status_code=400, detail="Max 50 assets per bulk run")

    celery = get_celery_app()
    jobs = []
    for asset_id in request.asset_ids:
        kwargs: dict = {"asset_id": asset_id}
        if request.session_date:
            kwargs["session_date"] = request.session_date
        result = celery.send_task(
            TASK_NAME_MAP["generate_market_analysis"],
            kwargs=kwargs,
            queue="fin-scraper",
        )
        jobs.append({"asset_id": asset_id, "job_id": result.id})

    return {
        "status": "queued",
        "jobs_dispatched": len(jobs),
        "jobs": jobs,
    }
