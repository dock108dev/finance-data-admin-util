"""Economic indicator endpoints — FRED macro data.

GET /api/economic/indicators  — List economic indicators with filters
GET /api/economic/latest      — Latest value for each tracked FRED series
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.economic import EconomicIndicator
from app.dependencies.auth import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


# ── Response Models ──────────────────────────────────────────────────────────

class EconomicIndicatorResponse(BaseModel):
    id: int
    series_id: str
    series_name: str
    category: str
    value: float
    observation_date: date
    source: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class LatestIndicatorResponse(BaseModel):
    series_id: str
    series_name: str
    category: str
    value: float
    observation_date: date
    source: str

    model_config = {"from_attributes": True}


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/indicators", response_model=list[EconomicIndicatorResponse])
async def list_indicators(
    series_id: str | None = Query(None),
    category: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List economic indicators with optional filters."""
    stmt = select(EconomicIndicator)

    if series_id:
        stmt = stmt.where(EconomicIndicator.series_id == series_id)
    if category:
        stmt = stmt.where(EconomicIndicator.category == category)
    if start_date:
        stmt = stmt.where(EconomicIndicator.observation_date >= start_date)
    if end_date:
        stmt = stmt.where(EconomicIndicator.observation_date <= end_date)

    stmt = stmt.order_by(EconomicIndicator.observation_date.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/latest", response_model=list[LatestIndicatorResponse])
async def get_latest_indicators(
    db: AsyncSession = Depends(get_db),
):
    """Get the latest value for each tracked FRED series."""
    # Subquery: max observation_date per series_id
    max_date_sub = (
        select(
            EconomicIndicator.series_id,
            func.max(EconomicIndicator.observation_date).label("max_date"),
        )
        .group_by(EconomicIndicator.series_id)
        .subquery()
    )

    stmt = (
        select(EconomicIndicator)
        .join(
            max_date_sub,
            (EconomicIndicator.series_id == max_date_sub.c.series_id)
            & (EconomicIndicator.observation_date == max_date_sub.c.max_date),
        )
        .order_by(EconomicIndicator.series_id)
    )

    result = await db.execute(stmt)
    return result.scalars().all()
