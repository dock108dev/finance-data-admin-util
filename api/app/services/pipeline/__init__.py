"""Market analysis pipeline — equivalent to sports-data-admin's 8-stage game flow pipeline.

Pipeline stages (adapted from game flow):

1. COLLECT_CANDLES     — Fetch + normalize OHLCV data for session
2. COMPUTE_INDICATORS  — Calculate RSI, MACD, BB, VWAP, etc.
3. VALIDATE_DATA       — Validate data quality (gaps, outliers)
4. DETECT_EVENTS       — Identify significant price/volume events
5. ANALYZE_SENTIMENT   — Merge social + news sentiment
6. GENERATE_NARRATIVE  — AI-powered market narrative (OpenAI)
7. VALIDATE_NARRATIVE  — Enforce guardrails (block count, word count)
8. FINALIZE            — Persist analysis + timeline to database

Semantic Roles (adapted from game flow):
    SETUP              — Pre-market context, overnight moves
    CATALYST           — Event that triggered the move (equiv. MOMENTUM_SHIFT)
    REACTION           — Market response to catalyst
    DECISION_POINT     — Key level test (support/resistance)
    RESOLUTION         — Session outcome and close
"""

from enum import Enum


class PipelineStage(str, Enum):
    COLLECT_CANDLES = "collect_candles"
    COMPUTE_INDICATORS = "compute_indicators"
    VALIDATE_DATA = "validate_data"
    DETECT_EVENTS = "detect_events"
    ANALYZE_SENTIMENT = "analyze_sentiment"
    GENERATE_NARRATIVE = "generate_narrative"
    VALIDATE_NARRATIVE = "validate_narrative"
    FINALIZE = "finalize"


class NarrativeRole(str, Enum):
    SETUP = "SETUP"
    CATALYST = "CATALYST"
    REACTION = "REACTION"
    DECISION_POINT = "DECISION_POINT"
    RESOLUTION = "RESOLUTION"


PIPELINE_STAGES_ORDERED = list(PipelineStage)
