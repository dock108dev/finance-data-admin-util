"""Monte Carlo portfolio simulation engine.

Equivalent to sports-data-admin's MLB simulator.
Simulates portfolio returns using historical signal performance.
"""

import math
import random
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SimulationResult:
    """Result of a Monte Carlo portfolio simulation."""
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


def run_simulation(
    signal_hit_rate: float,
    avg_return_per_signal: float,
    avg_loss_per_signal: float,
    signals_per_period: int,
    num_periods: int = 252,
    initial_capital: float = 10000.0,
    position_size_pct: float = 5.0,
    num_simulations: int = 1000,
    seed: int | None = None,
) -> SimulationResult:
    """Run Monte Carlo simulation of signal-based trading.

    Args:
        signal_hit_rate: Probability of a signal being correct (0-1).
        avg_return_per_signal: Average return when signal hits (%).
        avg_loss_per_signal: Average loss when signal misses (%).
        signals_per_period: Number of signals per trading period.
        num_periods: Number of trading periods to simulate.
        initial_capital: Starting capital.
        position_size_pct: Capital allocated per signal (%).
        num_simulations: Number of Monte Carlo iterations.
        seed: Random seed for reproducibility.
    """
    if seed is not None:
        random.seed(seed)

    final_values: list[float] = []
    max_drawdowns: list[float] = []
    sharpe_ratios: list[float] = []

    for _ in range(num_simulations):
        capital = initial_capital
        peak = capital
        max_dd = 0.0
        period_returns: list[float] = []

        for _ in range(num_periods):
            period_return = 0.0
            for _ in range(signals_per_period):
                position = capital * (position_size_pct / 100)
                if random.random() < signal_hit_rate:
                    pnl = position * (avg_return_per_signal / 100)
                else:
                    pnl = -position * (avg_loss_per_signal / 100)
                capital += pnl
                period_return += pnl

            period_returns.append(period_return / initial_capital if initial_capital > 0 else 0)

            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        final_values.append(capital)
        max_drawdowns.append(max_dd)

        # Sharpe ratio
        if len(period_returns) > 1:
            mean_r = sum(period_returns) / len(period_returns)
            var = sum((r - mean_r) ** 2 for r in period_returns) / (len(period_returns) - 1)
            std_r = math.sqrt(var) if var > 0 else 0
            sharpe = (mean_r / std_r) * math.sqrt(252) if std_r > 0 else 0
            sharpe_ratios.append(sharpe)

    final_values.sort()
    n = len(final_values)

    profitable = sum(1 for v in final_values if v > initial_capital)

    logger.info(
        "simulation.complete",
        num_simulations=num_simulations,
        mean_return_pct=round((sum(final_values) / n - initial_capital) / initial_capital * 100, 2),
    )

    return SimulationResult(
        num_simulations=num_simulations,
        num_periods=num_periods,
        initial_capital=initial_capital,
        mean_final_value=round(sum(final_values) / n, 2),
        median_final_value=round(final_values[n // 2], 2),
        std_final_value=round(
            math.sqrt(sum((v - sum(final_values) / n) ** 2 for v in final_values) / n), 2
        ),
        percentile_5=round(final_values[int(n * 0.05)], 2),
        percentile_25=round(final_values[int(n * 0.25)], 2),
        percentile_75=round(final_values[int(n * 0.75)], 2),
        percentile_95=round(final_values[int(n * 0.95)], 2),
        probability_of_profit=round(profitable / n * 100, 2),
        max_drawdown_mean=round(sum(max_drawdowns) / len(max_drawdowns) * 100, 2),
        sharpe_ratio_mean=round(sum(sharpe_ratios) / len(sharpe_ratios), 2) if sharpe_ratios else 0.0,
    )
