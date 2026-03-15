"""Signal endpoints — alpha signals and arbitrage — equivalent to fairbet routes.

GET /api/signals/alpha           — List alpha signals (filterable)
GET /api/signals/arbitrage       — Cross-exchange arbitrage opportunities
GET /api/signals/sentiment       — Sentiment snapshots
GET /api/signals/analysis/{id}   — Market analysis for a session
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.signals import AlphaSignal, MarketAnalysis
from app.db.exchanges import ArbitrageWork
from app.db.social import SentimentSnapshot
from app.dependencies.auth import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


# ── Response Models ──────────────────────────────────────────────────────────

class AlphaSignalResponse(BaseModel):
    id: int
    asset_id: int
    signal_type: str
    direction: str
    strength: float
    confidence_tier: str
    ev_estimate: float | None = None
    trigger_price: float | None = None
    target_price: float | None = None
    stop_loss: float | None = None
    risk_reward_ratio: float | None = None
    detected_at: datetime
    expires_at: datetime | None = None
    outcome: str | None = None
    disabled_reason: str | None = None
    derivation: dict | None = None

    model_config = {"from_attributes": True}


class ArbitrageResponse(BaseModel):
    asset_id: int
    pair_key: str
    exchange: str
    price: float
    bid: float | None = None
    ask: float | None = None
    spread_vs_reference: float | None = None
    arb_pct: float | None = None
    reference_exchange: str | None = None
    observed_at: datetime

    model_config = {"from_attributes": True}


class SentimentResponse(BaseModel):
    id: int
    asset_id: int | None = None
    fear_greed_index: int | None = None
    social_volume: int | None = None
    bullish_pct: float | None = None
    bearish_pct: float | None = None
    weighted_sentiment: float | None = None
    observed_at: datetime

    model_config = {"from_attributes": True}


class AnalysisResponse(BaseModel):
    id: int
    asset_id: int
    analysis_date: str
    summary: str | None = None
    key_moments_json: dict | None = None
    narrative_blocks_json: dict | None = None
    generated_by: str | None = None
    generated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/alpha", response_model=list[AlphaSignalResponse])
async def list_alpha_signals(
    asset_class: str | None = Query(None),
    signal_type: str | None = Query(None),
    confidence_tier: str | None = Query(None),
    direction: str | None = Query(None),
    min_strength: float = Query(0.0),
    outcome: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List alpha signals with filters.

    Equivalent to GET /api/fairbet/odds in sports-data-admin.
    """
    stmt = select(AlphaSignal).where(AlphaSignal.strength >= min_strength)

    if signal_type:
        stmt = stmt.where(AlphaSignal.signal_type == signal_type)
    if confidence_tier:
        stmt = stmt.where(AlphaSignal.confidence_tier == confidence_tier.upper())
    if direction:
        stmt = stmt.where(AlphaSignal.direction == direction.upper())
    if outcome:
        stmt = stmt.where(AlphaSignal.outcome == outcome)

    stmt = stmt.order_by(AlphaSignal.detected_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/arbitrage", response_model=list[ArbitrageResponse])
async def list_arbitrage_opportunities(
    asset_id: int | None = Query(None),
    min_arb_pct: float = Query(0.0),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List current cross-exchange arbitrage opportunities.

    Equivalent to the FairBet odds viewer in sports-data-admin.
    """
    stmt = select(ArbitrageWork)

    if asset_id:
        stmt = stmt.where(ArbitrageWork.asset_id == asset_id)
    if min_arb_pct > 0:
        stmt = stmt.where(ArbitrageWork.arb_pct >= min_arb_pct)

    stmt = stmt.order_by(ArbitrageWork.observed_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/sentiment", response_model=list[SentimentResponse])
async def list_sentiment(
    asset_id: int | None = Query(None),
    asset_class_id: int | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List sentiment snapshots."""
    stmt = select(SentimentSnapshot)

    if asset_id:
        stmt = stmt.where(SentimentSnapshot.asset_id == asset_id)
    if asset_class_id:
        stmt = stmt.where(SentimentSnapshot.asset_class_id == asset_class_id)

    stmt = stmt.order_by(SentimentSnapshot.observed_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/analysis/{session_id}", response_model=AnalysisResponse)
async def get_analysis(session_id: int, db: AsyncSession = Depends(get_db)):
    """Get market analysis for a session.

    Equivalent to GET /api/games/{id}/flow in sports-data-admin.
    """
    result = await db.execute(
        select(MarketAnalysis).where(MarketAnalysis.session_id == session_id)
        .order_by(MarketAnalysis.analysis_version.desc())
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis
