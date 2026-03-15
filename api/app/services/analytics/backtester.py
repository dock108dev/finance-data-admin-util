"""Signal backtesting engine — test signal strategies against historical data.

Equivalent to sports-data-admin's backtest functionality.
"""

from dataclasses import dataclass
from datetime import date

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class BacktestResult:
    """Result of a signal backtest run."""
    total_signals: int
    hit_count: int
    miss_count: int
    expired_count: int
    hit_rate: float
    avg_return_pct: float
    max_return_pct: float
    min_return_pct: float
    sharpe_ratio: float | None
    profit_factor: float | None
    by_signal_type: dict
    by_confidence_tier: dict


def run_backtest(
    signals: list[dict],
    outcomes: list[dict],
    start_date: date | None = None,
    end_date: date | None = None,
) -> BacktestResult:
    """Run a backtest over historical signals and their outcomes.

    Args:
        signals: List of signal dicts with signal_type, direction, strength, etc.
        outcomes: List of outcome dicts with signal_id, actual_return_pct, outcome.
        start_date: Filter signals after this date.
        end_date: Filter signals before this date.

    Returns:
        BacktestResult with aggregate performance metrics.
    """
    outcome_map = {o.get("signal_id"): o for o in outcomes}

    matched: list[dict] = []
    for sig in signals:
        outcome = outcome_map.get(sig.get("id"))
        if outcome:
            matched.append({**sig, **outcome})

    if not matched:
        return BacktestResult(
            total_signals=len(signals),
            hit_count=0, miss_count=0, expired_count=0,
            hit_rate=0.0, avg_return_pct=0.0,
            max_return_pct=0.0, min_return_pct=0.0,
            sharpe_ratio=None, profit_factor=None,
            by_signal_type={}, by_confidence_tier={},
        )

    hits = [m for m in matched if m.get("actual_outcome") == "HIT"]
    misses = [m for m in matched if m.get("actual_outcome") == "MISS"]
    expired = [m for m in matched if m.get("actual_outcome") == "EXPIRED"]

    returns = [m.get("actual_return_pct", 0) for m in matched if m.get("actual_return_pct") is not None]
    avg_return = sum(returns) / len(returns) if returns else 0.0

    # Sharpe ratio (simplified — annualized)
    sharpe = None
    if len(returns) > 1:
        import math
        mean_r = sum(returns) / len(returns)
        variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
        std = math.sqrt(variance) if variance > 0 else 0
        sharpe = round((mean_r / std) * math.sqrt(252), 2) if std > 0 else None

    # Profit factor
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else None

    # Breakdown by signal type
    by_type: dict = {}
    for m in matched:
        st = m.get("signal_type", "unknown")
        if st not in by_type:
            by_type[st] = {"total": 0, "hits": 0, "returns": []}
        by_type[st]["total"] += 1
        if m.get("actual_outcome") == "HIT":
            by_type[st]["hits"] += 1
        r = m.get("actual_return_pct")
        if r is not None:
            by_type[st]["returns"].append(r)

    for st, data in by_type.items():
        data["hit_rate"] = data["hits"] / data["total"] if data["total"] > 0 else 0
        data["avg_return"] = sum(data["returns"]) / len(data["returns"]) if data["returns"] else 0
        del data["returns"]

    # Breakdown by confidence tier
    by_tier: dict = {}
    for m in matched:
        tier = m.get("confidence_tier", "UNKNOWN")
        if tier not in by_tier:
            by_tier[tier] = {"total": 0, "hits": 0}
        by_tier[tier]["total"] += 1
        if m.get("actual_outcome") == "HIT":
            by_tier[tier]["hits"] += 1

    for tier, data in by_tier.items():
        data["hit_rate"] = data["hits"] / data["total"] if data["total"] > 0 else 0

    logger.info(
        "backtest.complete",
        total_signals=len(signals),
        matched=len(matched),
        hit_rate=round(len(hits) / len(matched) * 100, 1) if matched else 0,
    )

    return BacktestResult(
        total_signals=len(signals),
        hit_count=len(hits),
        miss_count=len(misses),
        expired_count=len(expired),
        hit_rate=round(len(hits) / len(matched) * 100, 2) if matched else 0.0,
        avg_return_pct=round(avg_return, 4),
        max_return_pct=round(max(returns), 4) if returns else 0.0,
        min_return_pct=round(min(returns), 4) if returns else 0.0,
        sharpe_ratio=sharpe,
        profit_factor=profit_factor,
        by_signal_type=by_type,
        by_confidence_tier=by_tier,
    )
