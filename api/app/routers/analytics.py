"""Analytics endpoints — ML models, backtesting, simulation.

Equivalent to sports-data-admin's analytics_routes.py.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.analytics import MLModel, FeatureConfig, TrainingJob, BacktestJob
from app.dependencies.auth import require_api_key
from app.services.analytics.simulator import run_simulation, SimulationResult

router = APIRouter(dependencies=[Depends(require_api_key)])


# ── Response Models ─────────────────────────────────────────────────────────

class MLModelResponse(BaseModel):
    id: int
    name: str
    model_type: str
    version: int
    asset_class: str | None
    is_active: bool
    is_production: bool
    description: str | None
    metrics: dict | None
    trained_at: str | None

    model_config = {"from_attributes": True}


class FeatureConfigResponse(BaseModel):
    id: int
    name: str
    model_type: str
    asset_class: str | None
    features: dict
    lookback_periods: int
    is_active: bool

    model_config = {"from_attributes": True}


class TrainingJobResponse(BaseModel):
    id: int
    model_id: int | None
    status: str
    metrics: dict | None
    started_at: str | None
    finished_at: str | None
    duration_seconds: float | None

    model_config = {"from_attributes": True}


class BacktestJobResponse(BaseModel):
    id: int
    name: str
    signal_type: str | None
    asset_class: str | None
    status: str
    results: dict | None
    started_at: str | None
    finished_at: str | None

    model_config = {"from_attributes": True}


class SimulationRequest(BaseModel):
    signal_hit_rate: float = 0.55
    avg_return_per_signal: float = 2.0
    avg_loss_per_signal: float = 1.5
    signals_per_period: int = 3
    num_periods: int = 252
    initial_capital: float = 10000.0
    position_size_pct: float = 5.0
    num_simulations: int = 1000
    seed: int | None = None


class SimulationResponse(BaseModel):
    num_simulations: int
    num_periods: int
    initial_capital: float
    mean_final_value: float
    median_final_value: float
    std_final_value: float
    percentile_5: float
    percentile_25: float
    percentile_75: float
    percentile_95: float
    probability_of_profit: float
    max_drawdown_mean: float
    sharpe_ratio_mean: float


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/models", response_model=list[MLModelResponse])
async def list_models(
    model_type: str | None = Query(None),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """List ML models."""
    stmt = select(MLModel)
    if model_type:
        stmt = stmt.where(MLModel.model_type == model_type)
    if active_only:
        stmt = stmt.where(MLModel.is_active.is_(True))
    stmt = stmt.order_by(MLModel.name, MLModel.version.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/features", response_model=list[FeatureConfigResponse])
async def list_feature_configs(
    model_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List feature configurations."""
    stmt = select(FeatureConfig)
    if model_type:
        stmt = stmt.where(FeatureConfig.model_type == model_type)
    stmt = stmt.order_by(FeatureConfig.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/training-jobs", response_model=list[TrainingJobResponse])
async def list_training_jobs(
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List training job runs."""
    stmt = select(TrainingJob)
    if status:
        stmt = stmt.where(TrainingJob.status == status)
    stmt = stmt.order_by(TrainingJob.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/backtests", response_model=list[BacktestJobResponse])
async def list_backtests(
    status: str | None = Query(None),
    signal_type: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List backtest job runs."""
    stmt = select(BacktestJob)
    if status:
        stmt = stmt.where(BacktestJob.status == status)
    if signal_type:
        stmt = stmt.where(BacktestJob.signal_type == signal_type)
    stmt = stmt.order_by(BacktestJob.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/simulate", response_model=SimulationResponse)
async def run_portfolio_simulation(request: SimulationRequest):
    """Run a Monte Carlo portfolio simulation."""
    result = run_simulation(
        signal_hit_rate=request.signal_hit_rate,
        avg_return_per_signal=request.avg_return_per_signal,
        avg_loss_per_signal=request.avg_loss_per_signal,
        signals_per_period=request.signals_per_period,
        num_periods=request.num_periods,
        initial_capital=request.initial_capital,
        position_size_pct=request.position_size_pct,
        num_simulations=request.num_simulations,
        seed=request.seed,
    )
    return SimulationResponse(
        num_simulations=result.num_simulations,
        num_periods=result.num_periods,
        initial_capital=result.initial_capital,
        mean_final_value=result.mean_final_value,
        median_final_value=result.median_final_value,
        std_final_value=result.std_final_value,
        percentile_5=result.percentile_5,
        percentile_25=result.percentile_25,
        percentile_75=result.percentile_75,
        percentile_95=result.percentile_95,
        probability_of_profit=result.probability_of_profit,
        max_drawdown_mean=result.max_drawdown_mean,
        sharpe_ratio_mean=result.sharpe_ratio_mean,
    )
