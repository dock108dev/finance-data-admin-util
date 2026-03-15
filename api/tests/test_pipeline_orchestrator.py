"""Tests for the 8-stage pipeline orchestrator."""

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.pipeline import PipelineStage, PIPELINE_STAGES_ORDERED
from app.services.pipeline.orchestrator import (
    AnalysisPipelineOrchestrator,
    PipelineError,
    PipelineResult,
)


def _mock_db():
    """Create a mock db that returns plausible query results for all stages."""
    db = AsyncMock()

    # Build a generic execute mock that handles each table query
    async def mock_execute(query, params=None):
        sql_str = str(query)
        result = MagicMock()

        if "fin_sessions" in sql_str:
            mapping = MagicMock()
            mapping.first.return_value = {
                "id": 1, "open_price": 100.0, "high_price": 105.0,
                "low_price": 98.0, "close_price": 103.0, "volume": 50000.0,
                "vwap": 101.5, "change_pct": 3.0, "status": "closed",
            }
            result.mappings.return_value = mapping
        elif "fin_candles" in sql_str and "5m" in sql_str:
            # Return enough candles for indicators to compute
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
            mapping.first.return_value = {"ticker": "TEST", "name": "Test Asset"}
            result.mappings.return_value = mapping
        elif "fin_market_analyses" in sql_str:
            result.fetchone.return_value = (1,)
        elif "fin_session_timelines" in sql_str:
            result.fetchone.return_value = (1,)
        else:
            mapping = MagicMock()
            mapping.first.return_value = None
            result.mappings.return_value = mapping

        return result

    db.execute = mock_execute
    db.flush = AsyncMock()
    return db


class TestPipelineResult:
    def test_construction(self):
        r = PipelineResult(PipelineStage.COLLECT_CANDLES, success=True, data={"key": 1})
        assert r.stage == PipelineStage.COLLECT_CANDLES
        assert r.success is True
        assert r.data == {"key": 1}

    def test_defaults(self):
        r = PipelineResult(PipelineStage.FINALIZE, success=False, error="boom")
        assert r.data == {}
        assert r.error == "boom"
        assert r.duration_ms == 0


class TestPipelineError:
    def test_construction(self):
        e = PipelineError(PipelineStage.VALIDATE_DATA, "bad data")
        assert e.stage == PipelineStage.VALIDATE_DATA
        assert "validate_data" in str(e)
        assert "bad data" in str(e)


class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_run_all_stages_succeeds(self):
        db = _mock_db()
        orch = AnalysisPipelineOrchestrator(db)

        mock_blocks = [
            {"role": "SETUP", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "CATALYST", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "RESOLUTION", "narrative": " ".join(["word"] * 50), "word_count": 50},
        ]

        with patch("app.services.openai_client.generate_market_narrative", new_callable=AsyncMock, return_value=mock_blocks), \
             patch("app.services.openai_client.apply_flow_pass", new_callable=AsyncMock, return_value=mock_blocks):
            results = await orch.run(asset_id=1, session_date=date(2024, 1, 15))

        assert len(results) == 8
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_stage_order(self):
        db = _mock_db()
        orch = AnalysisPipelineOrchestrator(db)

        mock_blocks = [
            {"role": "SETUP", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "CATALYST", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "RESOLUTION", "narrative": " ".join(["word"] * 50), "word_count": 50},
        ]

        with patch("app.services.openai_client.generate_market_narrative", new_callable=AsyncMock, return_value=mock_blocks), \
             patch("app.services.openai_client.apply_flow_pass", new_callable=AsyncMock, return_value=mock_blocks):
            results = await orch.run(asset_id=1, session_date=date(2024, 1, 15))

        for i, result in enumerate(results):
            assert result.stage == PIPELINE_STAGES_ORDERED[i]

    @pytest.mark.asyncio
    async def test_stops_on_failure(self):
        db = _mock_db()
        orch = AnalysisPipelineOrchestrator(db)

        async def _failing_handler(ctx):
            raise RuntimeError("stage failed")

        orch._stage_handlers[PipelineStage.COMPUTE_INDICATORS] = _failing_handler

        results = await orch.run(asset_id=1, session_date=date(2024, 1, 15))
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert "stage failed" in results[1].error

    @pytest.mark.asyncio
    async def test_resume_from_stage(self):
        db = _mock_db()
        orch = AnalysisPipelineOrchestrator(db)

        mock_blocks = [
            {"role": "SETUP", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "CATALYST", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "RESOLUTION", "narrative": " ".join(["word"] * 50), "word_count": 50},
        ]

        with patch("app.services.openai_client.generate_market_narrative", new_callable=AsyncMock, return_value=mock_blocks), \
             patch("app.services.openai_client.apply_flow_pass", new_callable=AsyncMock, return_value=mock_blocks):
            results = await orch.run(
                asset_id=1,
                session_date=date(2024, 1, 15),
                start_from=PipelineStage.DETECT_EVENTS,
            )

        assert results[0].stage == PipelineStage.DETECT_EVENTS
        # DETECT_EVENTS through FINALIZE = 5 stages
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_context_propagation(self):
        db = _mock_db()
        orch = AnalysisPipelineOrchestrator(db)

        captured_contexts = []
        original_compute = orch._stage_handlers[PipelineStage.COMPUTE_INDICATORS]

        async def _capture_ctx(ctx):
            captured_contexts.append(dict(ctx))
            return await original_compute(ctx)

        orch._stage_handlers[PipelineStage.COMPUTE_INDICATORS] = _capture_ctx

        mock_blocks = [
            {"role": "SETUP", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "RESOLUTION", "narrative": " ".join(["word"] * 50), "word_count": 50},
        ]

        with patch("app.services.openai_client.generate_market_narrative", new_callable=AsyncMock, return_value=mock_blocks), \
             patch("app.services.openai_client.apply_flow_pass", new_callable=AsyncMock, return_value=mock_blocks):
            await orch.run(asset_id=1, session_date=date(2024, 1, 15))

        assert len(captured_contexts) == 1
        ctx = captured_contexts[0]
        assert ctx["asset_id"] == 1
        assert ctx["candles_collected"] is True

    @pytest.mark.asyncio
    async def test_duration_tracking(self):
        db = _mock_db()
        orch = AnalysisPipelineOrchestrator(db)

        mock_blocks = [
            {"role": "SETUP", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "RESOLUTION", "narrative": " ".join(["word"] * 50), "word_count": 50},
        ]

        with patch("app.services.openai_client.generate_market_narrative", new_callable=AsyncMock, return_value=mock_blocks), \
             patch("app.services.openai_client.apply_flow_pass", new_callable=AsyncMock, return_value=mock_blocks):
            results = await orch.run(asset_id=1, session_date=date(2024, 1, 15))

        for r in results:
            assert r.duration_ms >= 0


class TestPipelineStages:
    def test_count(self):
        assert len(PIPELINE_STAGES_ORDERED) == 8

    def test_first_is_collect(self):
        assert PIPELINE_STAGES_ORDERED[0] == PipelineStage.COLLECT_CANDLES

    def test_last_is_finalize(self):
        assert PIPELINE_STAGES_ORDERED[-1] == PipelineStage.FINALIZE
