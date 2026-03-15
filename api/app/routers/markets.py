"""Public market data endpoints — equivalent to sports-data-admin's sports routes.

GET /api/markets/assets           — List assets (filterable by class, sector)
GET /api/markets/assets/{id}      — Asset detail
GET /api/markets/sessions         — List market sessions
GET /api/markets/sessions/{id}    — Session detail with OHLCV
GET /api/markets/candles/{id}     — Candle data for an asset
GET /api/markets/exchanges/{id}   — Cross-exchange prices
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.markets import Asset, AssetClass, MarketSession, Candle
from app.dependencies.auth import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


# ── Response Models ──────────────────────────────────────────────────────────

class AssetResponse(BaseModel):
    id: int
    asset_class_code: str | None = None
    ticker: str
    name: str
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    exchange: str | None = None
    is_active: bool = True
    last_price_at: datetime | None = None

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    id: int
    asset_id: int
    session_date: date
    open_price: float | None = None
    high_price: float | None = None
    low_price: float | None = None
    close_price: float | None = None
    volume: float | None = None
    change_pct: float | None = None
    status: str

    model_config = {"from_attributes": True}


class CandleResponse(BaseModel):
    timestamp: datetime
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str

    model_config = {"from_attributes": True}


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/assets", response_model=list[AssetResponse])
async def list_assets(
    asset_class: str | None = Query(None, description="Filter by asset class: STOCKS, CRYPTO"),
    sector: str | None = Query(None),
    is_active: bool = Query(True),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    """List all tracked assets with optional filters."""
    stmt = select(Asset).where(Asset.is_active == is_active)

    if asset_class:
        stmt = stmt.join(AssetClass).where(AssetClass.code == asset_class.upper())
    if sector:
        stmt = stmt.where(Asset.sector == sector)

    stmt = stmt.order_by(Asset.ticker).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single asset by ID."""
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    asset_id: int | None = Query(None),
    asset_class: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List market sessions with filters."""
    stmt = select(MarketSession)

    if asset_id:
        stmt = stmt.where(MarketSession.asset_id == asset_id)
    if asset_class:
        stmt = stmt.join(AssetClass).where(AssetClass.code == asset_class.upper())
    if start_date:
        stmt = stmt.where(MarketSession.session_date >= start_date)
    if end_date:
        stmt = stmt.where(MarketSession.session_date <= end_date)
    if status:
        stmt = stmt.where(MarketSession.status == status)

    stmt = stmt.order_by(MarketSession.session_date.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single session by ID."""
    result = await db.execute(
        select(MarketSession).where(MarketSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/assets/{asset_id}/sessions", response_model=list[SessionResponse])
async def list_asset_sessions(
    asset_id: int,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List sessions for a specific asset (convenience endpoint)."""
    stmt = select(MarketSession).where(MarketSession.asset_id == asset_id)

    if start_date:
        stmt = stmt.where(MarketSession.session_date >= start_date)
    if end_date:
        stmt = stmt.where(MarketSession.session_date <= end_date)

    stmt = stmt.order_by(MarketSession.session_date.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/candles/{asset_id}", response_model=list[CandleResponse])
async def get_candles(
    asset_id: int,
    interval: str = Query("5m", description="Candle interval: 1m, 5m, 15m, 1h, 1d"),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    limit: int = Query(500, le=2000),
    db: AsyncSession = Depends(get_db),
):
    """Get OHLCV candle data for an asset."""
    stmt = (
        select(Candle)
        .where(Candle.asset_id == asset_id, Candle.interval == interval)
    )

    if start:
        stmt = stmt.where(Candle.timestamp >= start)
    if end:
        stmt = stmt.where(Candle.timestamp <= end)

    stmt = stmt.order_by(Candle.timestamp.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
