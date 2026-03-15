"""Scraper and pipeline execution tracking models.

Equivalent to sports-data-admin's scraper.py + pipeline.py + resolution.py.

Mapping:
    sports_scrape_runs    → fin_scrape_runs
    sports_job_runs       → fin_job_runs
    sports_game_conflicts → fin_data_conflicts
"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ScrapeRun(Base):
    """Individual scraper execution record — equivalent to sports_scrape_runs."""

    __tablename__ = "fin_scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scraper_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # "price_ingest", "exchange_sync", "social_collect", "onchain_sync",
    # "signal_pipeline", "analysis_generation", "daily_sweep"
    asset_class_id: Mapped[int | None] = mapped_column(ForeignKey("fin_asset_classes.id"))

    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # "pending", "running", "completed", "failed", "interrupted"

    # Execution info
    job_id: Mapped[str | None] = mapped_column(String(100))
    requested_by: Mapped[str | None] = mapped_column(String(50))
    # "celery_beat", "admin_manual", "trigger"
    config: Mapped[dict | None] = mapped_column(JSONB)
    # Task parameters

    # Results
    summary: Mapped[str | None] = mapped_column(Text)
    error_details: Mapped[str | None] = mapped_column(Text)
    assets_processed: Mapped[int | None] = mapped_column(Integer)
    records_created: Mapped[int | None] = mapped_column(Integer)
    records_updated: Mapped[int | None] = mapped_column(Integer)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_scrape_runs_type", "scraper_type"),
        Index("idx_scrape_runs_status", "status"),
        Index("idx_scrape_runs_started", "started_at"),
    )


class JobRun(Base):
    """Pipeline phase execution record — equivalent to sports_job_runs."""

    __tablename__ = "fin_job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phase: Mapped[str] = mapped_column(String(100), nullable=False)
    # "price_ingestion_stocks", "signal_pipeline_crypto", etc.
    asset_classes: Mapped[list | None] = mapped_column(JSONB)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    # Results
    error_summary: Mapped[str | None] = mapped_column(Text)
    summary_data: Mapped[dict | None] = mapped_column(JSONB)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    __table_args__ = (
        Index("idx_job_runs_phase", "phase"),
        Index("idx_job_runs_started", "started_at"),
    )


class PipelineStageRun(Base):
    """Individual pipeline stage execution record.

    Tracks each stage within a pipeline job execution, giving visibility
    into which stage failed and why.
    Equivalent to sports-data-admin's GamePipelineStage.
    """

    __tablename__ = "fin_pipeline_stage_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_run_id: Mapped[int] = mapped_column(ForeignKey("fin_job_runs.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    # collect_candles, compute_indicators, validate_data, detect_events,
    # analyze_sentiment, generate_narrative, validate_narrative, finalize

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # pending, running, completed, failed, skipped

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[float | None] = mapped_column(Float)
    output_json: Mapped[dict | None] = mapped_column(JSONB)
    error_details: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    __table_args__ = (
        Index("idx_pipeline_stages_job_run", "job_run_id"),
        Index("idx_pipeline_stages_stage", "stage"),
        Index("idx_pipeline_stages_status", "status"),
    )


class DataConflict(Base, TimestampMixin):
    """Data conflict / duplicate detection — equivalent to sports_game_conflicts."""

    __tablename__ = "fin_data_conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_class_id: Mapped[int | None] = mapped_column(ForeignKey("fin_asset_classes.id"))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("fin_assets.id"))

    conflict_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # "duplicate_candle", "price_mismatch", "missing_data", "stale_data"
    source: Mapped[str | None] = mapped_column(String(50))
    conflict_fields: Mapped[dict | None] = mapped_column(JSONB)
    description: Mapped[str | None] = mapped_column(Text)

    # Resolution
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_conflicts_type", "conflict_type"),
        Index("idx_conflicts_unresolved", "resolved_at"),
    )
