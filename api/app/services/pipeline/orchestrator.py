"""Pipeline orchestrator — runs the 8-stage market analysis pipeline.

Equivalent to sports-data-admin's pipeline orchestrator that runs
game flow generation through all 8 stages sequentially.
"""

import json
from datetime import date, datetime, timezone

import structlog
from sqlalchemy import select, text, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pipeline import PipelineStage, NarrativeRole, PIPELINE_STAGES_ORDERED
from app.services.alpha import (
    compute_rsi,
    compute_macd,
    compute_bollinger_bands,
)

logger = structlog.get_logger(__name__)


class PipelineError(Exception):
    """Raised when a pipeline stage fails."""

    def __init__(self, stage: PipelineStage, message: str):
        self.stage = stage
        super().__init__(f"[{stage.value}] {message}")


class PipelineResult:
    """Result of a single pipeline stage execution."""

    def __init__(self, stage: PipelineStage, success: bool, data: dict | None = None,
                 error: str | None = None, duration_ms: float = 0):
        self.stage = stage
        self.success = success
        self.data = data or {}
        self.error = error
        self.duration_ms = duration_ms


class AnalysisPipelineOrchestrator:
    """Orchestrates the 8-stage market analysis pipeline.

    Usage:
        orchestrator = AnalysisPipelineOrchestrator(db_session)
        results = await orchestrator.run(asset_id=1, session_date=date.today())
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self._stage_handlers: dict[PipelineStage, callable] = {
            PipelineStage.COLLECT_CANDLES: self._collect_candles,
            PipelineStage.COMPUTE_INDICATORS: self._compute_indicators,
            PipelineStage.VALIDATE_DATA: self._validate_data,
            PipelineStage.DETECT_EVENTS: self._detect_events,
            PipelineStage.ANALYZE_SENTIMENT: self._analyze_sentiment,
            PipelineStage.GENERATE_NARRATIVE: self._generate_narrative,
            PipelineStage.VALIDATE_NARRATIVE: self._validate_narrative,
            PipelineStage.FINALIZE: self._finalize,
        }

    async def run(
        self,
        asset_id: int,
        session_date,
        start_from: PipelineStage | None = None,
    ) -> list[PipelineResult]:
        """Execute all pipeline stages sequentially.

        Args:
            asset_id: The asset to analyze.
            session_date: The trading session date.
            start_from: Optional stage to resume from (skip prior stages).

        Returns:
            List of PipelineResult for each stage executed.
        """
        results: list[PipelineResult] = []
        context: dict = {
            "asset_id": asset_id,
            "session_date": session_date,
        }

        started = start_from is None
        for stage in PIPELINE_STAGES_ORDERED:
            if not started:
                if stage == start_from:
                    started = True
                else:
                    continue

            logger.info("pipeline.stage_start", stage=stage.value, asset_id=asset_id)
            start_time = datetime.utcnow()

            try:
                handler = self._stage_handlers[stage]
                stage_data = await handler(context)
                context.update(stage_data or {})

                elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
                result = PipelineResult(stage, success=True, data=stage_data,
                                        duration_ms=elapsed)
                logger.info("pipeline.stage_complete", stage=stage.value,
                            duration_ms=elapsed)

            except Exception as e:
                elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
                result = PipelineResult(stage, success=False, error=str(e),
                                        duration_ms=elapsed)
                logger.error("pipeline.stage_failed", stage=stage.value,
                             error=str(e), duration_ms=elapsed)
                results.append(result)
                break  # Stop pipeline on failure

            results.append(result)

        return results

    # ── Stage Implementations ────────────────────────────────────────────

    async def _collect_candles(self, ctx: dict) -> dict:
        """Stage 1: Fetch and normalize OHLCV candles for the session."""
        asset_id = ctx["asset_id"]
        session_date = ctx["session_date"]
        if isinstance(session_date, str):
            session_date = date.fromisoformat(session_date)

        logger.info("pipeline.collect_candles", asset_id=asset_id, session_date=str(session_date))

        # Query session for this asset + date
        session_row = await self.db.execute(
            text("""
                SELECT id, open_price, high_price, low_price, close_price,
                       volume, vwap, change_pct, status
                FROM fin_sessions
                WHERE asset_id = :asset_id AND session_date = :session_date
                LIMIT 1
            """),
            {"asset_id": asset_id, "session_date": session_date},
        )
        session = session_row.mappings().first()

        session_dict = {}
        session_id = None
        if session:
            session_id = session["id"]
            session_dict = {
                "session_id": session["id"],
                "open": session["open_price"],
                "high": session["high_price"],
                "low": session["low_price"],
                "close": session["close_price"],
                "volume": session["volume"],
                "vwap": session["vwap"],
                "change_pct": session["change_pct"],
                "status": session["status"],
            }

        # Query candles — prefer 5m interval, fall back to 1d
        candle_rows = await self.db.execute(
            text("""
                SELECT timestamp, open, high, low, close, volume, vwap, interval
                FROM fin_candles
                WHERE asset_id = :asset_id
                  AND timestamp::date = :session_date
                  AND interval = '5m'
                ORDER BY timestamp ASC
            """),
            {"asset_id": asset_id, "session_date": session_date},
        )
        candles = [dict(r._mapping) for r in candle_rows]

        # Fall back to 1d candles if no 5m data
        if not candles:
            candle_rows = await self.db.execute(
                text("""
                    SELECT timestamp, open, high, low, close, volume, vwap, interval
                    FROM fin_candles
                    WHERE asset_id = :asset_id
                      AND timestamp::date = :session_date
                      AND interval = '1d'
                    ORDER BY timestamp ASC
                """),
                {"asset_id": asset_id, "session_date": session_date},
            )
            candles = [dict(r._mapping) for r in candle_rows]

        # Convert timestamps to strings for JSON serialization
        for c in candles:
            if isinstance(c.get("timestamp"), datetime):
                c["timestamp"] = c["timestamp"].isoformat()

        return {
            "candles_collected": True,
            "candle_count": len(candles),
            "candles": candles,
            "session": session_dict,
            "session_id": session_id,
        }

    async def _compute_indicators(self, ctx: dict) -> dict:
        """Stage 2: Calculate technical indicators (RSI, MACD, BB, VWAP)."""
        asset_id = ctx["asset_id"]
        candles = ctx.get("candles", [])

        logger.info("pipeline.compute_indicators", asset_id=asset_id, candle_count=len(candles))

        if not candles:
            return {
                "indicators_computed": True,
                "indicators": {},
                "indicator_summary": {},
            }

        closes = [c["close"] for c in candles if c.get("close") is not None]
        volumes = [c["volume"] for c in candles if c.get("volume") is not None]

        indicators: dict = {}

        # RSI-14
        rsi = compute_rsi(closes, period=14)
        if rsi is not None:
            indicators["rsi_14"] = rsi

        # MACD (12/26/9)
        macd_result = compute_macd(closes, fast=12, slow=26, signal_period=9)
        if macd_result is not None:
            macd_line, signal_line, histogram = macd_result
            indicators["macd_line"] = macd_line
            indicators["macd_signal"] = signal_line
            indicators["macd_histogram"] = histogram

        # Bollinger Bands (20, 2)
        bb = compute_bollinger_bands(closes, period=20, num_std=2.0)
        if bb is not None:
            upper, middle, lower = bb
            indicators["bb_upper"] = upper
            indicators["bb_middle"] = middle
            indicators["bb_lower"] = lower

        # VWAP (volume-weighted average price)
        if closes and volumes and len(closes) == len(volumes):
            total_vp = sum(c * v for c, v in zip(closes, volumes))
            total_v = sum(volumes)
            if total_v > 0:
                indicators["vwap"] = round(total_vp / total_v, 4)

        # Current price for reference
        if closes:
            indicators["current_price"] = closes[-1]

        return {
            "indicators_computed": True,
            "indicators": indicators,
            "indicator_summary": {
                "rsi_14": indicators.get("rsi_14"),
                "macd_histogram": indicators.get("macd_histogram"),
                "bb_position": _bb_position(
                    closes[-1] if closes else None,
                    indicators.get("bb_upper"),
                    indicators.get("bb_lower"),
                ),
                "vwap": indicators.get("vwap"),
            },
        }

    async def _validate_data(self, ctx: dict) -> dict:
        """Stage 3: Validate data quality — gaps, outliers, stale data."""
        asset_id = ctx["asset_id"]
        candles = ctx.get("candles", [])

        logger.info("pipeline.validate_data", asset_id=asset_id, candle_count=len(candles))

        warnings: list[str] = []
        quality_status = "PASSED"

        # Check minimum candle count
        if len(candles) == 0:
            quality_status = "FAILED"
            warnings.append("No candles found for session")
            return {
                "data_valid": False,
                "warnings": warnings,
                "quality_status": quality_status,
            }

        interval = candles[0].get("interval", "1d") if candles else "1d"

        if interval == "5m" and len(candles) < 10:
            quality_status = "DEGRADED"
            warnings.append(f"Low candle count: {len(candles)} (expected >10 for 5m)")

        # Check for price being flat (all closes identical)
        closes = [c["close"] for c in candles if c.get("close") is not None]
        if closes and len(set(closes)) == 1:
            quality_status = "DEGRADED"
            warnings.append("Price is flat across all candles")

        # Check volume > 0
        volumes = [c["volume"] for c in candles if c.get("volume") is not None]
        zero_vol = sum(1 for v in volumes if v == 0)
        if zero_vol > len(volumes) * 0.5:
            quality_status = "DEGRADED"
            warnings.append(f"{zero_vol}/{len(volumes)} candles have zero volume")

        # Check for outliers: any candle where |change| > 20% from previous
        outliers = []
        for i in range(1, len(closes)):
            if closes[i - 1] == 0:
                continue
            change_pct = abs((closes[i] - closes[i - 1]) / closes[i - 1]) * 100
            if change_pct > 20:
                outliers.append({
                    "index": i,
                    "change_pct": round(change_pct, 2),
                    "from_price": closes[i - 1],
                    "to_price": closes[i],
                })

        if outliers:
            quality_status = "DEGRADED"
            warnings.append(f"{len(outliers)} outlier candle(s) detected (>20% change)")

        # Check for time gaps (>5 min gap for 5m candles)
        if interval == "5m" and len(candles) > 1:
            gap_count = 0
            for i in range(1, len(candles)):
                ts_curr = candles[i].get("timestamp", "")
                ts_prev = candles[i - 1].get("timestamp", "")
                if ts_curr and ts_prev:
                    try:
                        if isinstance(ts_curr, str):
                            t1 = datetime.fromisoformat(ts_curr)
                        else:
                            t1 = ts_curr
                        if isinstance(ts_prev, str):
                            t0 = datetime.fromisoformat(ts_prev)
                        else:
                            t0 = ts_prev
                        gap_min = (t1 - t0).total_seconds() / 60
                        if gap_min > 10:  # More than 2x the expected interval
                            gap_count += 1
                    except (ValueError, TypeError):
                        pass
            if gap_count > 0:
                warnings.append(f"{gap_count} time gap(s) detected in candle series")

        data_valid = quality_status != "FAILED"

        return {
            "data_valid": data_valid,
            "warnings": warnings,
            "quality_status": quality_status,
            "outliers": outliers,
        }

    async def _detect_events(self, ctx: dict) -> dict:
        """Stage 4: Identify significant price/volume events (key moments)."""
        asset_id = ctx["asset_id"]
        candles = ctx.get("candles", [])
        indicators = ctx.get("indicators", {})

        logger.info("pipeline.detect_events", asset_id=asset_id)

        events: list[dict] = []

        if not candles:
            return {"events_detected": 0, "events": [], "key_moments": []}

        closes = [c["close"] for c in candles if c.get("close") is not None]
        volumes = [c["volume"] for c in candles if c.get("volume") is not None]
        avg_volume = sum(volumes) / len(volumes) if volumes else 0

        # Bollinger Band breach detection
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")

        for i, candle in enumerate(candles):
            price = candle.get("close")
            vol = candle.get("volume", 0)
            ts = candle.get("timestamp", "")

            if price is None:
                continue

            # Volume spike: >3x average
            if avg_volume > 0 and vol > 3 * avg_volume:
                events.append({
                    "timestamp": ts,
                    "event_type": "VOLUME_SPIKE",
                    "role": NarrativeRole.CATALYST.value,
                    "description": f"Volume spike at {vol:.0f} ({vol/avg_volume:.1f}x avg)",
                    "price": price,
                    "volume": vol,
                })

            # BB breach (breakout)
            if bb_upper and price > bb_upper:
                events.append({
                    "timestamp": ts,
                    "event_type": "BB_UPPER_BREACH",
                    "role": NarrativeRole.CATALYST.value,
                    "description": f"Price {price:.2f} broke above upper BB {bb_upper:.2f}",
                    "price": price,
                    "volume": vol,
                })
            elif bb_lower and price < bb_lower:
                events.append({
                    "timestamp": ts,
                    "event_type": "BB_LOWER_BREACH",
                    "role": NarrativeRole.CATALYST.value,
                    "description": f"Price {price:.2f} broke below lower BB {bb_lower:.2f}",
                    "price": price,
                    "volume": vol,
                })

            # Large price move from previous candle
            if i > 0 and closes[i - 1] != 0:
                move_pct = ((price - closes[i - 1]) / closes[i - 1]) * 100
                if abs(move_pct) > 2:  # >2% move in a single candle
                    direction = "up" if move_pct > 0 else "down"
                    events.append({
                        "timestamp": ts,
                        "event_type": "LARGE_MOVE",
                        "role": NarrativeRole.REACTION.value,
                        "description": f"Sharp {direction} move of {move_pct:+.2f}%",
                        "price": price,
                        "volume": vol,
                    })

        # RSI extremes
        rsi = indicators.get("rsi_14")
        if rsi is not None:
            if rsi < 30:
                events.append({
                    "timestamp": candles[-1].get("timestamp", ""),
                    "event_type": "RSI_OVERSOLD",
                    "role": NarrativeRole.DECISION_POINT.value,
                    "description": f"RSI at {rsi:.1f} — oversold territory",
                    "price": closes[-1] if closes else None,
                    "volume": volumes[-1] if volumes else None,
                })
            elif rsi > 70:
                events.append({
                    "timestamp": candles[-1].get("timestamp", ""),
                    "event_type": "RSI_OVERBOUGHT",
                    "role": NarrativeRole.DECISION_POINT.value,
                    "description": f"RSI at {rsi:.1f} — overbought territory",
                    "price": closes[-1] if closes else None,
                    "volume": volumes[-1] if volumes else None,
                })

        # Support/resistance test — check if session high/low are near round numbers
        session = ctx.get("session", {})
        session_high = session.get("high")
        session_low = session.get("low")
        if session_high and session_low:
            # Simple round-number proximity check
            for level in [session_high, session_low]:
                magnitude = 10 ** max(0, len(str(int(level))) - 2) if level >= 1 else 1
                nearest = round(level / magnitude) * magnitude
                if abs(level - nearest) / nearest < 0.005:  # Within 0.5%
                    events.append({
                        "timestamp": "",
                        "event_type": "LEVEL_TEST",
                        "role": NarrativeRole.DECISION_POINT.value,
                        "description": f"Price tested round level {nearest:.0f}",
                        "price": level,
                        "volume": None,
                    })

        # Deduplicate: keep at most 10 events, prioritize catalysts
        role_priority = {
            NarrativeRole.CATALYST.value: 0,
            NarrativeRole.DECISION_POINT.value: 1,
            NarrativeRole.REACTION.value: 2,
            NarrativeRole.SETUP.value: 3,
            NarrativeRole.RESOLUTION.value: 4,
        }
        events.sort(key=lambda e: role_priority.get(e.get("role", ""), 5))
        events = events[:10]

        return {
            "events_detected": len(events),
            "events": events,
            "key_moments": events[:5],  # Top 5 for narrative
        }

    async def _analyze_sentiment(self, ctx: dict) -> dict:
        """Stage 5: Merge social + news sentiment for the session window."""
        asset_id = ctx["asset_id"]
        session_date = ctx["session_date"]
        if isinstance(session_date, str):
            session_date = date.fromisoformat(session_date)

        logger.info("pipeline.analyze_sentiment", asset_id=asset_id)

        # Query social posts for asset within session window
        social_result = await self.db.execute(
            text("""
                SELECT COUNT(*) as cnt,
                       AVG(sentiment_score) as avg_sentiment
                FROM fin_social_posts
                WHERE asset_id = :asset_id
                  AND posted_at::date = :session_date
            """),
            {"asset_id": asset_id, "session_date": session_date},
        )
        social_row = social_result.mappings().first()
        social_count = social_row["cnt"] if social_row else 0
        social_sentiment = social_row["avg_sentiment"] if social_row and social_row["avg_sentiment"] else 0.0

        # Query news articles
        news_result = await self.db.execute(
            text("""
                SELECT COUNT(*) as cnt,
                       AVG(sentiment_score) as avg_sentiment
                FROM fin_news_articles
                WHERE asset_id = :asset_id
                  AND published_at::date = :session_date
            """),
            {"asset_id": asset_id, "session_date": session_date},
        )
        news_row = news_result.mappings().first()
        news_count = news_row["cnt"] if news_row else 0
        news_sentiment = news_row["avg_sentiment"] if news_row and news_row["avg_sentiment"] else 0.0

        # Query sentiment snapshots
        snapshot_result = await self.db.execute(
            text("""
                SELECT fear_greed_index, weighted_sentiment
                FROM fin_sentiment_snapshots
                WHERE asset_id = :asset_id
                  AND observed_at::date = :session_date
                ORDER BY observed_at DESC
                LIMIT 1
            """),
            {"asset_id": asset_id, "session_date": session_date},
        )
        snapshot = snapshot_result.mappings().first()
        fear_greed = snapshot["fear_greed_index"] if snapshot else None
        weighted = snapshot["weighted_sentiment"] if snapshot else None

        # Compute weighted sentiment score
        # Weight: social (0.3), news (0.3), snapshot (0.4)
        components = []
        if social_sentiment:
            components.append((social_sentiment, 0.3))
        if news_sentiment:
            components.append((news_sentiment, 0.3))
        if weighted is not None:
            components.append((weighted, 0.4))

        if components:
            total_weight = sum(w for _, w in components)
            sentiment_score = sum(s * w for s, w in components) / total_weight
        else:
            sentiment_score = 0.0

        return {
            "sentiment_analyzed": True,
            "sentiment_score": round(sentiment_score, 4),
            "social_posts": social_count,
            "news_articles": news_count,
            "fear_greed_index": fear_greed,
            "social_sentiment": round(social_sentiment, 4) if social_sentiment else 0.0,
            "news_sentiment": round(news_sentiment, 4) if news_sentiment else 0.0,
        }

    async def _generate_narrative(self, ctx: dict) -> dict:
        """Stage 6: Generate AI-powered market narrative (OpenAI)."""
        asset_id = ctx["asset_id"]
        session = ctx.get("session", {})
        events = ctx.get("events", [])
        indicators = ctx.get("indicators", {})

        logger.info("pipeline.generate_narrative", asset_id=asset_id)

        candle_summary = {
            "open": session.get("open"),
            "high": session.get("high"),
            "low": session.get("low"),
            "close": session.get("close"),
            "volume": session.get("volume"),
            "change_pct": session.get("change_pct"),
            "candle_count": ctx.get("candle_count", 0),
        }

        sentiment = {
            "sentiment_score": ctx.get("sentiment_score", 0),
            "social_posts": ctx.get("social_posts", 0),
            "news_articles": ctx.get("news_articles", 0),
            "fear_greed_index": ctx.get("fear_greed_index"),
        }

        from app.services.openai_client import generate_market_narrative, apply_flow_pass

        # Pass 1: Generate blocks
        blocks = await generate_market_narrative(
            candle_summary=candle_summary,
            events=events,
            sentiment=sentiment,
            indicators=ctx.get("indicator_summary", indicators),
        )

        # Pass 2: Flow smoothing
        if blocks:
            # Look up asset ticker for context
            asset_result = await self.db.execute(
                text("SELECT ticker, name FROM fin_assets WHERE id = :id"),
                {"id": asset_id},
            )
            asset_row = asset_result.mappings().first()
            asset_context = f"{asset_row['ticker']} ({asset_row['name']})" if asset_row else f"Asset {asset_id}"

            blocks = await apply_flow_pass(blocks, asset_context=asset_context)

        return {
            "narrative_generated": True,
            "blocks": blocks,
        }

    async def _validate_narrative(self, ctx: dict) -> dict:
        """Stage 7: Enforce narrative guardrails."""
        blocks = ctx.get("blocks", [])

        logger.info("pipeline.validate_narrative", asset_id=ctx["asset_id"], block_count=len(blocks))

        warnings: list[str] = []
        narrative_valid = True

        # Block count: 3-5 (hard limit)
        if len(blocks) < 3:
            warnings.append(f"Too few blocks: {len(blocks)} (minimum 3)")
            narrative_valid = False
        elif len(blocks) > 5:
            warnings.append(f"Too many blocks: {len(blocks)} (maximum 5)")
            # Trim to 5 — keep first (SETUP), last (RESOLUTION), and 3 middle
            if len(blocks) > 5:
                blocks = blocks[:4] + [blocks[-1]]
                warnings.append("Trimmed to 5 blocks")

        # Words per block: 30-120 (warning)
        total_words = 0
        for i, block in enumerate(blocks):
            wc = block.get("word_count", len(block.get("narrative", "").split()))
            total_words += wc
            if wc < 30:
                warnings.append(f"Block {i+1} ({block.get('role')}): only {wc} words (min 30)")
            elif wc > 120:
                warnings.append(f"Block {i+1} ({block.get('role')}): {wc} words (max 120)")

        # Total words: ≤500 (warning)
        if total_words > 500:
            warnings.append(f"Total word count {total_words} exceeds 500")

        # Must have SETUP first and RESOLUTION last
        if blocks:
            if blocks[0].get("role") != NarrativeRole.SETUP.value:
                warnings.append(f"First block role is '{blocks[0].get('role')}', expected SETUP")
                narrative_valid = False
            if blocks[-1].get("role") != NarrativeRole.RESOLUTION.value:
                warnings.append(f"Last block role is '{blocks[-1].get('role')}', expected RESOLUTION")
                narrative_valid = False

        # Strip forbidden language (re-check after flow pass)
        from app.services.openai_client import strip_forbidden_language
        for block in blocks:
            cleaned = strip_forbidden_language(block.get("narrative", ""))
            if cleaned != block.get("narrative"):
                warnings.append(f"Forbidden language removed from {block.get('role')} block")
                block["narrative"] = cleaned
                block["word_count"] = len(cleaned.split())

        return {
            "narrative_valid": narrative_valid,
            "guardrail_warnings": warnings,
            "validated_blocks": blocks,
        }

    async def _finalize(self, ctx: dict) -> dict:
        """Stage 8: Persist analysis + timeline to database."""
        asset_id = ctx["asset_id"]
        session_date = ctx["session_date"]
        session_id = ctx.get("session_id")
        blocks = ctx.get("validated_blocks", ctx.get("blocks", []))
        events = ctx.get("events", [])
        indicators = ctx.get("indicators", {})
        session = ctx.get("session", {})

        if isinstance(session_date, str):
            session_date = date.fromisoformat(session_date)

        logger.info("pipeline.finalize", asset_id=asset_id, session_id=session_id)

        now = datetime.now(timezone.utc)

        # Build summary from first and last block narratives
        summary_parts = []
        if blocks:
            summary_parts.append(blocks[0].get("narrative", "")[:200])
            if len(blocks) > 1:
                summary_parts.append(blocks[-1].get("narrative", "")[:200])
        summary = " ".join(summary_parts) if summary_parts else "No narrative generated."

        # Create/update MarketAnalysis
        analysis_result = await self.db.execute(
            text("""
                INSERT INTO fin_market_analyses
                    (asset_id, session_id, analysis_date, key_moments_json,
                     narrative_blocks_json, summary, analysis_version,
                     generated_by, generated_at, created_at, updated_at)
                VALUES
                    (:asset_id, :session_id, :analysis_date, :key_moments,
                     :narrative_blocks, :summary, 1,
                     'openai-gpt-4o', :generated_at, :now, :now)
                ON CONFLICT ON CONSTRAINT uq_market_analysis_identity
                DO UPDATE SET
                    key_moments_json = EXCLUDED.key_moments_json,
                    narrative_blocks_json = EXCLUDED.narrative_blocks_json,
                    summary = EXCLUDED.summary,
                    generated_at = EXCLUDED.generated_at,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """),
            {
                "asset_id": asset_id,
                "session_id": session_id,
                "analysis_date": session_date,
                "key_moments": json.dumps(events[:5]) if events else None,
                "narrative_blocks": json.dumps(blocks) if blocks else None,
                "summary": summary,
                "generated_at": now,
                "now": now,
            },
        )
        analysis_row = analysis_result.fetchone()
        analysis_id = analysis_row[0] if analysis_row else None

        # Create/update SessionTimeline
        timeline_id = None
        if session_id:
            # Build timeline from candles + events
            timeline_data = {
                "candle_count": ctx.get("candle_count", 0),
                "events": events,
                "indicators": indicators,
            }
            market_analysis_data = {
                "quality_status": ctx.get("quality_status", "UNKNOWN"),
                "sentiment_score": ctx.get("sentiment_score", 0),
                "narrative_valid": ctx.get("narrative_valid", False),
                "guardrail_warnings": ctx.get("guardrail_warnings", []),
            }
            summary_data = {
                "session": session,
                "indicator_summary": ctx.get("indicator_summary", {}),
            }

            timeline_result = await self.db.execute(
                text("""
                    INSERT INTO fin_session_timelines
                        (session_id, asset_id, timeline_json, market_analysis_json,
                         summary_json, timeline_version, generated_at, generated_by,
                         generation_reason, created_at, updated_at)
                    VALUES
                        (:session_id, :asset_id, :timeline_json, :market_analysis_json,
                         :summary_json, 1, :generated_at, 'pipeline',
                         'daily_analysis', :now, :now)
                    ON CONFLICT ON CONSTRAINT uq_session_timeline_identity
                    DO UPDATE SET
                        timeline_json = EXCLUDED.timeline_json,
                        market_analysis_json = EXCLUDED.market_analysis_json,
                        summary_json = EXCLUDED.summary_json,
                        generated_at = EXCLUDED.generated_at,
                        updated_at = EXCLUDED.updated_at
                    RETURNING id
                """),
                {
                    "session_id": session_id,
                    "asset_id": asset_id,
                    "timeline_json": json.dumps(timeline_data),
                    "market_analysis_json": json.dumps(market_analysis_data),
                    "summary_json": json.dumps(summary_data),
                    "generated_at": now,
                    "now": now,
                },
            )
            timeline_row = timeline_result.fetchone()
            timeline_id = timeline_row[0] if timeline_row else None

        await self.db.flush()

        return {
            "finalized": True,
            "analysis_id": analysis_id,
            "timeline_id": timeline_id,
        }


# ── Helpers ─────────────────────────────────────────────────────────────────

def _bb_position(price: float | None, upper: float | None, lower: float | None) -> str | None:
    """Describe price position relative to Bollinger Bands."""
    if price is None or upper is None or lower is None:
        return None
    if price > upper:
        return "ABOVE_UPPER"
    elif price < lower:
        return "BELOW_LOWER"
    else:
        band_width = upper - lower
        if band_width == 0:
            return "MIDDLE"
        position = (price - lower) / band_width
        if position > 0.8:
            return "NEAR_UPPER"
        elif position < 0.2:
            return "NEAR_LOWER"
        return "MIDDLE"
