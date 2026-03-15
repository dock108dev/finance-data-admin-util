"""Tests for the pipeline runner — JobRun lifecycle management."""

import json
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.pipeline.runner import (
    run_pipeline_for_asset,
    _create_job_run,
    _record_stage_run,
    _complete_job_run,
    _fail_job_run,
)
from app.services.pipeline.orchestrator import PipelineResult
from app.services.pipeline import PipelineStage


def _mock_db_for_runner():
    """Create a mock async DB that handles runner SQL queries."""
    db = AsyncMock()

    async def mock_execute(query, params=None):
        sql_str = str(query)
        result = MagicMock()
        if "INSERT INTO fin_job_runs" in sql_str:
            result.fetchone.return_value = (42,)
        elif "INSERT INTO fin_pipeline_stage_runs" in sql_str:
            pass  # No return needed
        elif "UPDATE fin_job_runs" in sql_str:
            pass
        elif "fin_sessions" in sql_str:
            mapping = MagicMock()
            mapping.first.return_value = {
                "id": 1, "open_price": 100.0, "high_price": 105.0,
                "low_price": 98.0, "close_price": 103.0, "volume": 50000.0,
                "vwap": 101.5, "change_pct": 3.0, "status": "closed",
            }
            result.mappings.return_value = mapping
        elif "fin_candles" in sql_str and "5m" in sql_str:
            candles = []
            price = 100.0
            for i in range(40):
                delta = (i % 5 - 2) * 0.5
                candles.append({
                    "timestamp": f"2024-01-15T10:{i:02d}:00+00:00",
                    "open": price, "high": price + 0.3, "low": price - 0.3,
                    "close": price + delta, "volume": 1000 + i * 100,
                    "vwap": None, "interval": "5m",
                })
                price += delta
            mock_rows = []
            for c in candles:
                row = MagicMock()
                row._mapping = c
                mock_rows.append(row)
            result.__iter__ = lambda self: iter(mock_rows)
        elif "fin_candles" in sql_str:
            result.__iter__ = lambda self: iter([])
        elif "fin_social_posts" in sql_str:
            mapping = MagicMock()
            mapping.first.return_value = {"cnt": 0, "avg_sentiment": None}
            result.mappings.return_value = mapping
        elif "fin_news_articles" in sql_str:
            mapping = MagicMock()
            mapping.first.return_value = {"cnt": 0, "avg_sentiment": None}
            result.mappings.return_value = mapping
        elif "fin_sentiment_snapshots" in sql_str:
            mapping = MagicMock()
            mapping.first.return_value = None
            result.mappings.return_value = mapping
        elif "fin_assets" in sql_str:
            mapping = MagicMock()
            mapping.first.return_value = {"ticker": "TEST", "name": "Test"}
            result.mappings.return_value = mapping
        elif "fin_market_analyses" in sql_str:
            result.fetchone.return_value = (1,)
        elif "fin_session_timelines" in sql_str:
            result.fetchone.return_value = (1,)
        else:
            result.fetchone.return_value = None
        return result

    db.execute = mock_execute
    db.flush = AsyncMock()
    return db


class TestCreateJobRun:
    @pytest.mark.asyncio
    async def test_creates_job_run(self):
        db = _mock_db_for_runner()
        job_id = await _create_job_run(db, asset_id=1, started_at=datetime.now(timezone.utc))
        assert job_id == 42

    @pytest.mark.asyncio
    async def test_handles_failure(self):
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=Exception("DB error"))
        db.flush = AsyncMock()
        job_id = await _create_job_run(db, asset_id=1, started_at=datetime.now(timezone.utc))
        assert job_id == -1


class TestRecordStageRun:
    @pytest.mark.asyncio
    async def test_records_success(self):
        db = _mock_db_for_runner()
        result = PipelineResult(PipelineStage.COLLECT_CANDLES, success=True,
                                data={"candle_count": 40}, duration_ms=123.4)
        await _record_stage_run(db, job_run_id=42, result=result,
                                pipeline_start=datetime.now(timezone.utc))

    @pytest.mark.asyncio
    async def test_records_failure(self):
        db = _mock_db_for_runner()
        result = PipelineResult(PipelineStage.VALIDATE_DATA, success=False,
                                error="bad data", duration_ms=50.0)
        await _record_stage_run(db, job_run_id=42, result=result,
                                pipeline_start=datetime.now(timezone.utc))

    @pytest.mark.asyncio
    async def test_handles_db_error(self):
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=Exception("insert failed"))
        result = PipelineResult(PipelineStage.FINALIZE, success=True, duration_ms=10)
        # Should not raise
        await _record_stage_run(db, job_run_id=42, result=result,
                                pipeline_start=datetime.now(timezone.utc))


class TestCompleteJobRun:
    @pytest.mark.asyncio
    async def test_marks_completed(self):
        db = _mock_db_for_runner()
        results = [
            PipelineResult(PipelineStage.COLLECT_CANDLES, success=True, duration_ms=100),
            PipelineResult(PipelineStage.FINALIZE, success=True, duration_ms=50),
        ]
        await _complete_job_run(db, job_run_id=42,
                                finished_at=datetime.now(timezone.utc),
                                duration=1.5, results=results)

    @pytest.mark.asyncio
    async def test_skips_invalid_id(self):
        db = AsyncMock()
        await _complete_job_run(db, job_run_id=-1,
                                finished_at=datetime.now(timezone.utc),
                                duration=1.0, results=[])
        db.execute.assert_not_called()


class TestFailJobRun:
    @pytest.mark.asyncio
    async def test_marks_failed(self):
        db = _mock_db_for_runner()
        await _fail_job_run(db, job_run_id=42,
                            finished_at=datetime.now(timezone.utc),
                            duration=0.5, error_summary="stage crashed")

    @pytest.mark.asyncio
    async def test_skips_invalid_id(self):
        db = AsyncMock()
        await _fail_job_run(db, job_run_id=-1,
                            finished_at=datetime.now(timezone.utc),
                            duration=0.5, error_summary="ignored")
        db.execute.assert_not_called()


class TestRunPipelineForAsset:
    @pytest.mark.asyncio
    async def test_full_pipeline_run(self):
        db = _mock_db_for_runner()

        mock_blocks = [
            {"role": "SETUP", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "CATALYST", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "RESOLUTION", "narrative": " ".join(["word"] * 50), "word_count": 50},
        ]

        with patch("app.services.openai_client.generate_market_narrative",
                    new_callable=AsyncMock, return_value=mock_blocks), \
             patch("app.services.openai_client.apply_flow_pass",
                    new_callable=AsyncMock, return_value=mock_blocks):

            result = await run_pipeline_for_asset(db, asset_id=1,
                                                  session_date=date(2024, 1, 15))

        assert result["status"] == "completed"
        assert result["job_run_id"] == 42
        assert result["stages_run"] == 8
        assert result["asset_id"] == 1
        assert len(result["stage_results"]) == 8
        assert all(s["success"] for s in result["stage_results"])

    @pytest.mark.asyncio
    async def test_pipeline_with_failure(self):
        db = _mock_db_for_runner()

        with patch("app.services.pipeline.orchestrator.AnalysisPipelineOrchestrator.run",
                    new_callable=AsyncMock) as mock_run:
            mock_run.return_value = [
                PipelineResult(PipelineStage.COLLECT_CANDLES, success=True, duration_ms=10),
                PipelineResult(PipelineStage.COMPUTE_INDICATORS, success=False,
                               error="compute failed", duration_ms=5),
            ]

            result = await run_pipeline_for_asset(db, asset_id=1)

        assert result["status"] == "failed"
        assert result["stages_run"] == 2
