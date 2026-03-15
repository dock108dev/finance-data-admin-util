"""Tests for the 8 pipeline stage handlers with real logic."""

import json
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.pipeline import PipelineStage, NarrativeRole
from app.services.pipeline.orchestrator import (
    AnalysisPipelineOrchestrator,
    PipelineResult,
    _bb_position,
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_candle(ts: str, o: float, h: float, l: float, c: float, v: float):
    """Create a candle dict."""
    return {
        "timestamp": ts,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
        "vwap": None,
        "interval": "5m",
    }


def _sample_candles(count: int = 40, base_price: float = 100.0):
    """Generate sample candle data for testing."""
    candles = []
    price = base_price
    for i in range(count):
        ts = f"2024-01-15T09:{30 + (i * 5) // 60:02d}:{(i * 5) % 60:02d}:00+00:00"
        delta = (i % 5 - 2) * 0.5  # small price movement
        o = price
        c = price + delta
        h = max(o, c) + 0.3
        l = min(o, c) - 0.3
        v = 1000 + i * 100
        candles.append(_make_candle(ts, o, h, l, c, v))
        price = c
    return candles


def _mock_db_for_collect(candles=None, session=None):
    """Create a mock db session that returns candle/session data."""
    db = AsyncMock()

    # Session query result
    session_data = session or {
        "id": 42,
        "open_price": 100.0,
        "high_price": 105.0,
        "low_price": 98.0,
        "close_price": 103.0,
        "volume": 50000.0,
        "vwap": 101.5,
        "change_pct": 3.0,
        "status": "closed",
    }

    session_result = MagicMock()
    session_mapping = MagicMock()
    session_mapping.first.return_value = session_data
    session_result.mappings.return_value = session_mapping

    # Candle query results
    candle_data = candles or _sample_candles()
    candle_result = MagicMock()

    # Create mock rows with _mapping attribute
    mock_rows = []
    for c in candle_data:
        row = MagicMock()
        row._mapping = c
        mock_rows.append(row)
    candle_result.__iter__ = lambda self: iter(mock_rows)

    # Empty fallback result
    empty_result = MagicMock()
    empty_result.__iter__ = lambda self: iter([])

    call_count = {"n": 0}

    async def mock_execute(query, params=None):
        call_count["n"] += 1
        sql_str = str(query)
        if "fin_sessions" in sql_str:
            return session_result
        elif "fin_candles" in sql_str and "5m" in sql_str:
            return candle_result
        elif "fin_candles" in sql_str:
            return empty_result
        elif "fin_social_posts" in sql_str:
            social_result = MagicMock()
            social_mapping = MagicMock()
            social_mapping.first.return_value = {"cnt": 5, "avg_sentiment": 0.3}
            social_result.mappings.return_value = social_mapping
            return social_result
        elif "fin_news_articles" in sql_str:
            news_result = MagicMock()
            news_mapping = MagicMock()
            news_mapping.first.return_value = {"cnt": 3, "avg_sentiment": 0.2}
            news_result.mappings.return_value = news_mapping
            return news_result
        elif "fin_sentiment_snapshots" in sql_str:
            snap_result = MagicMock()
            snap_mapping = MagicMock()
            snap_mapping.first.return_value = {"fear_greed_index": 65, "weighted_sentiment": 0.4}
            snap_result.mappings.return_value = snap_mapping
            return snap_result
        elif "fin_assets" in sql_str:
            asset_result = MagicMock()
            asset_mapping = MagicMock()
            asset_mapping.first.return_value = {"ticker": "AAPL", "name": "Apple Inc."}
            asset_result.mappings.return_value = asset_mapping
            return asset_result
        elif "fin_market_analyses" in sql_str:
            insert_result = MagicMock()
            insert_result.fetchone.return_value = (1,)
            return insert_result
        elif "fin_session_timelines" in sql_str:
            insert_result = MagicMock()
            insert_result.fetchone.return_value = (1,)
            return insert_result
        return MagicMock()

    db.execute = mock_execute
    db.flush = AsyncMock()
    return db


# ── Stage 1: Collect Candles ────────────────────────────────────────────────

class TestCollectCandles:
    @pytest.mark.asyncio
    async def test_collects_candles_and_session(self):
        db = _mock_db_for_collect()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._collect_candles({
            "asset_id": 1,
            "session_date": date(2024, 1, 15),
        })
        assert result["candles_collected"] is True
        assert result["candle_count"] == 40
        assert len(result["candles"]) == 40
        assert result["session"]["open"] == 100.0
        assert result["session_id"] == 42

    @pytest.mark.asyncio
    async def test_empty_candles(self):
        """When no candles exist, both 5m and 1d queries return empty."""
        db = AsyncMock()

        session_result = MagicMock()
        session_mapping = MagicMock()
        session_mapping.first.return_value = {
            "id": 42, "open_price": 100.0, "high_price": 105.0,
            "low_price": 98.0, "close_price": 103.0, "volume": 50000.0,
            "vwap": 101.5, "change_pct": 3.0, "status": "closed",
        }
        session_result.mappings.return_value = session_mapping

        empty_result = MagicMock()
        empty_result.__iter__ = lambda self: iter([])

        async def mock_execute(query, params=None):
            sql_str = str(query)
            if "fin_sessions" in sql_str:
                return session_result
            return empty_result

        db.execute = mock_execute
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._collect_candles({
            "asset_id": 1,
            "session_date": date(2024, 1, 15),
        })
        assert result["candle_count"] == 0


# ── Stage 2: Compute Indicators ────────────────────────────────────────────

class TestComputeIndicators:
    @pytest.mark.asyncio
    async def test_computes_rsi_macd_bb_vwap(self):
        candles = _sample_candles(count=40)
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._compute_indicators({
            "asset_id": 1,
            "candles": candles,
        })
        assert result["indicators_computed"] is True
        indicators = result["indicators"]
        assert "rsi_14" in indicators
        assert "macd_line" in indicators
        assert "bb_upper" in indicators
        assert "vwap" in indicators

    @pytest.mark.asyncio
    async def test_rsi_value_range(self):
        candles = _sample_candles(count=40)
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._compute_indicators({
            "asset_id": 1,
            "candles": candles,
        })
        rsi = result["indicators"]["rsi_14"]
        assert 0 <= rsi <= 100

    @pytest.mark.asyncio
    async def test_empty_candles_returns_empty_indicators(self):
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._compute_indicators({
            "asset_id": 1,
            "candles": [],
        })
        assert result["indicators"] == {}


# ── Stage 3: Validate Data ─────────────────────────────────────────────────

class TestValidateData:
    @pytest.mark.asyncio
    async def test_good_data_passes(self):
        candles = _sample_candles(count=40)
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._validate_data({
            "asset_id": 1,
            "candles": candles,
        })
        assert result["data_valid"] is True
        assert result["quality_status"] == "PASSED"

    @pytest.mark.asyncio
    async def test_no_candles_fails(self):
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._validate_data({
            "asset_id": 1,
            "candles": [],
        })
        assert result["data_valid"] is False
        assert result["quality_status"] == "FAILED"

    @pytest.mark.asyncio
    async def test_low_count_degrades(self):
        candles = _sample_candles(count=5)
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._validate_data({
            "asset_id": 1,
            "candles": candles,
        })
        assert result["quality_status"] == "DEGRADED"
        assert any("Low candle count" in w for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_flat_price_degrades(self):
        # All candles at same price
        candles = [_make_candle(f"2024-01-15T10:{i:02d}:00+00:00", 100, 100, 100, 100, 1000)
                   for i in range(20)]
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._validate_data({
            "asset_id": 1,
            "candles": candles,
        })
        assert result["quality_status"] == "DEGRADED"
        assert any("flat" in w for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_outlier_detection(self):
        candles = _sample_candles(count=20)
        # Inject an outlier: 50% price jump
        candles[10] = _make_candle("2024-01-15T10:20:00+00:00", 100, 160, 98, 150, 5000)
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._validate_data({
            "asset_id": 1,
            "candles": candles,
        })
        assert result["quality_status"] == "DEGRADED"
        assert len(result["outliers"]) > 0


# ── Stage 4: Detect Events ─────────────────────────────────────────────────

class TestDetectEvents:
    @pytest.mark.asyncio
    async def test_volume_spike_detection(self):
        candles = _sample_candles(count=20)
        # Inject a volume spike
        candles[10]["volume"] = 100000  # Way above average
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._detect_events({
            "asset_id": 1,
            "candles": candles,
            "indicators": {},
            "session": {},
        })
        volume_events = [e for e in result["events"] if e["event_type"] == "VOLUME_SPIKE"]
        assert len(volume_events) > 0
        assert volume_events[0]["role"] == NarrativeRole.CATALYST.value

    @pytest.mark.asyncio
    async def test_bb_breach_detection(self):
        candles = _sample_candles(count=20)
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._detect_events({
            "asset_id": 1,
            "candles": candles,
            "indicators": {"bb_upper": 90.0, "bb_lower": 80.0},  # All prices above BB
            "session": {},
        })
        bb_events = [e for e in result["events"] if "BB" in e["event_type"]]
        assert len(bb_events) > 0

    @pytest.mark.asyncio
    async def test_rsi_extreme_detection(self):
        candles = _sample_candles(count=20)
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._detect_events({
            "asset_id": 1,
            "candles": candles,
            "indicators": {"rsi_14": 25.0},  # Oversold
            "session": {},
        })
        rsi_events = [e for e in result["events"] if e["event_type"] == "RSI_OVERSOLD"]
        assert len(rsi_events) == 1
        assert rsi_events[0]["role"] == NarrativeRole.DECISION_POINT.value

    @pytest.mark.asyncio
    async def test_empty_candles_returns_no_events(self):
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._detect_events({
            "asset_id": 1,
            "candles": [],
            "indicators": {},
            "session": {},
        })
        assert result["events_detected"] == 0

    @pytest.mark.asyncio
    async def test_events_capped_at_10(self):
        # Create candles that would generate many events
        candles = []
        for i in range(30):
            candles.append(_make_candle(
                f"2024-01-15T10:{i:02d}:00+00:00",
                100, 200, 50, 100, 100000,  # Huge volume + price range
            ))
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._detect_events({
            "asset_id": 1,
            "candles": candles,
            "indicators": {"bb_upper": 90, "bb_lower": 110, "rsi_14": 25},
            "session": {},
        })
        assert len(result["events"]) <= 10


# ── Stage 5: Analyze Sentiment ─────────────────────────────────────────────

class TestAnalyzeSentiment:
    @pytest.mark.asyncio
    async def test_aggregates_sentiment(self):
        db = _mock_db_for_collect()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._analyze_sentiment({
            "asset_id": 1,
            "session_date": date(2024, 1, 15),
        })
        assert result["sentiment_analyzed"] is True
        assert result["social_posts"] == 5
        assert result["news_articles"] == 3
        assert result["fear_greed_index"] == 65
        assert isinstance(result["sentiment_score"], float)


# ── Stage 6: Generate Narrative ─────────────────────────────────────────────

class TestGenerateNarrative:
    @pytest.mark.asyncio
    async def test_generates_blocks(self):
        mock_blocks = [
            {"role": "SETUP", "narrative": "The session opened with bullish sentiment.", "word_count": 7},
            {"role": "CATALYST", "narrative": "Volume surged on earnings news.", "word_count": 6},
            {"role": "RESOLUTION", "narrative": "The session closed near highs.", "word_count": 7},
        ]

        db = _mock_db_for_collect()
        orch = AnalysisPipelineOrchestrator(db)

        with patch("app.services.openai_client.generate_market_narrative", new_callable=AsyncMock) as mock_gen, \
             patch("app.services.openai_client.apply_flow_pass", new_callable=AsyncMock) as mock_flow:
            mock_gen.return_value = mock_blocks
            mock_flow.return_value = mock_blocks

            result = await orch._generate_narrative({
                "asset_id": 1,
                "session": {"open": 100, "high": 105, "low": 98, "close": 103, "volume": 50000, "change_pct": 3.0},
                "events": [],
                "indicators": {},
                "candle_count": 40,
                "sentiment_score": 0.3,
                "social_posts": 5,
                "news_articles": 3,
                "fear_greed_index": 65,
            })

            assert result["narrative_generated"] is True
            assert len(result["blocks"]) == 3
            mock_gen.assert_called_once()
            mock_flow.assert_called_once()


# ── Stage 7: Validate Narrative ─────────────────────────────────────────────

class TestValidateNarrative:
    @pytest.mark.asyncio
    async def test_valid_narrative_passes(self):
        blocks = [
            {"role": "SETUP", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "CATALYST", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "RESOLUTION", "narrative": " ".join(["word"] * 50), "word_count": 50},
        ]
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._validate_narrative({
            "asset_id": 1,
            "blocks": blocks,
        })
        assert result["narrative_valid"] is True

    @pytest.mark.asyncio
    async def test_too_few_blocks_fails(self):
        blocks = [
            {"role": "SETUP", "narrative": " ".join(["word"] * 50), "word_count": 50},
        ]
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._validate_narrative({
            "asset_id": 1,
            "blocks": blocks,
        })
        assert result["narrative_valid"] is False
        assert any("Too few blocks" in w for w in result["guardrail_warnings"])

    @pytest.mark.asyncio
    async def test_too_many_blocks_trimmed(self):
        blocks = [
            {"role": "SETUP", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "CATALYST", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "REACTION", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "DECISION_POINT", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "REACTION", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "RESOLUTION", "narrative": " ".join(["word"] * 50), "word_count": 50},
        ]
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._validate_narrative({
            "asset_id": 1,
            "blocks": blocks,
        })
        assert any("Too many blocks" in w for w in result["guardrail_warnings"])

    @pytest.mark.asyncio
    async def test_wrong_first_role_fails(self):
        blocks = [
            {"role": "CATALYST", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "REACTION", "narrative": " ".join(["word"] * 50), "word_count": 50},
            {"role": "RESOLUTION", "narrative": " ".join(["word"] * 50), "word_count": 50},
        ]
        db = AsyncMock()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._validate_narrative({
            "asset_id": 1,
            "blocks": blocks,
        })
        assert result["narrative_valid"] is False
        assert any("SETUP" in w for w in result["guardrail_warnings"])


# ── Stage 8: Finalize ──────────────────────────────────────────────────────

class TestFinalize:
    @pytest.mark.asyncio
    async def test_persists_analysis_and_timeline(self):
        db = _mock_db_for_collect()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._finalize({
            "asset_id": 1,
            "session_date": date(2024, 1, 15),
            "session_id": 42,
            "validated_blocks": [
                {"role": "SETUP", "narrative": "Test setup.", "word_count": 2},
                {"role": "RESOLUTION", "narrative": "Test resolution.", "word_count": 2},
            ],
            "events": [{"event_type": "TEST", "description": "Test event"}],
            "indicators": {"rsi_14": 55.0},
            "session": {"open": 100, "close": 103},
        })
        assert result["finalized"] is True
        assert result["analysis_id"] == 1
        assert result["timeline_id"] == 1

    @pytest.mark.asyncio
    async def test_finalize_without_session_id(self):
        db = _mock_db_for_collect()
        orch = AnalysisPipelineOrchestrator(db)
        result = await orch._finalize({
            "asset_id": 1,
            "session_date": "2024-01-15",
            "session_id": None,
            "blocks": [],
            "events": [],
            "indicators": {},
            "session": {},
        })
        assert result["finalized"] is True
        assert result["timeline_id"] is None


# ── Helper Tests ───────────────────────────────────────────────────────────

class TestBBPosition:
    def test_above_upper(self):
        assert _bb_position(110, 105, 95) == "ABOVE_UPPER"

    def test_below_lower(self):
        assert _bb_position(90, 105, 95) == "BELOW_LOWER"

    def test_middle(self):
        assert _bb_position(100, 105, 95) == "MIDDLE"

    def test_near_upper(self):
        assert _bb_position(104, 105, 95) == "NEAR_UPPER"

    def test_near_lower(self):
        assert _bb_position(96, 105, 95) == "NEAR_LOWER"

    def test_none_inputs(self):
        assert _bb_position(None, 105, 95) is None
        assert _bb_position(100, None, 95) is None
