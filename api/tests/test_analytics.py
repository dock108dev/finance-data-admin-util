"""Tests for analytics engine — backtester, simulator, and router."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.analytics.backtester import run_backtest, BacktestResult
from app.services.analytics.simulator import run_simulation, SimulationResult


# ── Backtester Tests ────────────────────────────────────────────────────────

class TestBacktester:
    def test_no_signals(self):
        result = run_backtest([], [])
        assert result.total_signals == 0
        assert result.hit_rate == 0.0

    def test_no_matches(self):
        signals = [{"id": 1, "signal_type": "TECHNICAL"}]
        outcomes = [{"signal_id": 999, "actual_outcome": "HIT", "actual_return_pct": 2.0}]
        result = run_backtest(signals, outcomes)
        assert result.total_signals == 1
        assert result.hit_count == 0

    def test_all_hits(self):
        signals = [
            {"id": 1, "signal_type": "TECHNICAL", "confidence_tier": "HIGH"},
            {"id": 2, "signal_type": "TECHNICAL", "confidence_tier": "HIGH"},
        ]
        outcomes = [
            {"signal_id": 1, "actual_outcome": "HIT", "actual_return_pct": 3.0},
            {"signal_id": 2, "actual_outcome": "HIT", "actual_return_pct": 2.0},
        ]
        result = run_backtest(signals, outcomes)
        assert result.hit_count == 2
        assert result.miss_count == 0
        assert result.hit_rate == 100.0
        assert result.avg_return_pct == 2.5

    def test_mixed_outcomes(self):
        signals = [
            {"id": 1, "signal_type": "TECHNICAL", "confidence_tier": "HIGH"},
            {"id": 2, "signal_type": "SENTIMENT", "confidence_tier": "MEDIUM"},
            {"id": 3, "signal_type": "TECHNICAL", "confidence_tier": "LOW"},
        ]
        outcomes = [
            {"signal_id": 1, "actual_outcome": "HIT", "actual_return_pct": 5.0},
            {"signal_id": 2, "actual_outcome": "MISS", "actual_return_pct": -2.0},
            {"signal_id": 3, "actual_outcome": "EXPIRED", "actual_return_pct": 0.0},
        ]
        result = run_backtest(signals, outcomes)
        assert result.hit_count == 1
        assert result.miss_count == 1
        assert result.expired_count == 1
        assert result.total_signals == 3

    def test_by_signal_type_breakdown(self):
        signals = [
            {"id": 1, "signal_type": "TECHNICAL", "confidence_tier": "HIGH"},
            {"id": 2, "signal_type": "TECHNICAL", "confidence_tier": "HIGH"},
            {"id": 3, "signal_type": "SENTIMENT", "confidence_tier": "MEDIUM"},
        ]
        outcomes = [
            {"signal_id": 1, "actual_outcome": "HIT", "actual_return_pct": 3.0},
            {"signal_id": 2, "actual_outcome": "MISS", "actual_return_pct": -1.0},
            {"signal_id": 3, "actual_outcome": "HIT", "actual_return_pct": 2.0},
        ]
        result = run_backtest(signals, outcomes)
        assert "TECHNICAL" in result.by_signal_type
        assert "SENTIMENT" in result.by_signal_type
        assert result.by_signal_type["TECHNICAL"]["total"] == 2
        assert result.by_signal_type["SENTIMENT"]["hits"] == 1

    def test_by_confidence_tier_breakdown(self):
        signals = [
            {"id": 1, "signal_type": "T", "confidence_tier": "HIGH"},
            {"id": 2, "signal_type": "T", "confidence_tier": "LOW"},
        ]
        outcomes = [
            {"signal_id": 1, "actual_outcome": "HIT", "actual_return_pct": 2.0},
            {"signal_id": 2, "actual_outcome": "MISS", "actual_return_pct": -1.0},
        ]
        result = run_backtest(signals, outcomes)
        assert "HIGH" in result.by_confidence_tier
        assert result.by_confidence_tier["HIGH"]["hit_rate"] == 1.0

    def test_sharpe_ratio_computed(self):
        signals = [{"id": i, "signal_type": "T", "confidence_tier": "H"} for i in range(10)]
        outcomes = [
            {"signal_id": i, "actual_outcome": "HIT" if i % 2 == 0 else "MISS",
             "actual_return_pct": 2.0 if i % 2 == 0 else -1.0}
            for i in range(10)
        ]
        result = run_backtest(signals, outcomes)
        assert result.sharpe_ratio is not None

    def test_profit_factor(self):
        signals = [{"id": i, "signal_type": "T", "confidence_tier": "H"} for i in range(4)]
        outcomes = [
            {"signal_id": 0, "actual_outcome": "HIT", "actual_return_pct": 5.0},
            {"signal_id": 1, "actual_outcome": "HIT", "actual_return_pct": 3.0},
            {"signal_id": 2, "actual_outcome": "MISS", "actual_return_pct": -2.0},
            {"signal_id": 3, "actual_outcome": "MISS", "actual_return_pct": -1.0},
        ]
        result = run_backtest(signals, outcomes)
        assert result.profit_factor is not None
        # Profit factor = (5+3)/(2+1) = 2.67
        assert result.profit_factor == pytest.approx(2.67, abs=0.01)


# ── Simulator Tests ─────────────────────────────────────────────────────────

class TestSimulator:
    def test_basic_simulation(self):
        result = run_simulation(
            signal_hit_rate=0.55,
            avg_return_per_signal=2.0,
            avg_loss_per_signal=1.5,
            signals_per_period=2,
            num_periods=20,
            initial_capital=10000,
            num_simulations=100,
            seed=42,
        )
        assert isinstance(result, SimulationResult)
        assert result.num_simulations == 100
        assert result.num_periods == 20
        assert result.initial_capital == 10000

    def test_deterministic_with_seed(self):
        r1 = run_simulation(
            signal_hit_rate=0.6, avg_return_per_signal=2.0,
            avg_loss_per_signal=1.0, signals_per_period=3,
            num_periods=50, num_simulations=50, seed=123,
        )
        r2 = run_simulation(
            signal_hit_rate=0.6, avg_return_per_signal=2.0,
            avg_loss_per_signal=1.0, signals_per_period=3,
            num_periods=50, num_simulations=50, seed=123,
        )
        assert r1.mean_final_value == r2.mean_final_value
        assert r1.median_final_value == r2.median_final_value

    def test_high_hit_rate_profitable(self):
        result = run_simulation(
            signal_hit_rate=0.8,
            avg_return_per_signal=3.0,
            avg_loss_per_signal=1.0,
            signals_per_period=5,
            num_periods=100,
            initial_capital=10000,
            num_simulations=200,
            seed=42,
        )
        assert result.probability_of_profit > 80
        assert result.mean_final_value > 10000

    def test_low_hit_rate_unprofitable(self):
        result = run_simulation(
            signal_hit_rate=0.3,
            avg_return_per_signal=1.0,
            avg_loss_per_signal=2.0,
            signals_per_period=5,
            num_periods=100,
            initial_capital=10000,
            num_simulations=200,
            seed=42,
        )
        assert result.probability_of_profit < 50

    def test_percentiles_ordered(self):
        result = run_simulation(
            signal_hit_rate=0.55, avg_return_per_signal=2.0,
            avg_loss_per_signal=1.5, signals_per_period=3,
            num_periods=50, num_simulations=500, seed=42,
        )
        assert result.percentile_5 <= result.percentile_25
        assert result.percentile_25 <= result.median_final_value
        assert result.median_final_value <= result.percentile_75
        assert result.percentile_75 <= result.percentile_95

    def test_max_drawdown_positive(self):
        result = run_simulation(
            signal_hit_rate=0.5, avg_return_per_signal=2.0,
            avg_loss_per_signal=2.0, signals_per_period=3,
            num_periods=50, num_simulations=100, seed=42,
        )
        assert result.max_drawdown_mean >= 0


# ── Analytics Router Tests ──────────────────────────────────────────────────

def _mock_scalars(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


class TestAnalyticsRouter:
    @pytest.mark.asyncio
    async def test_list_models(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/analytics/models", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_features(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/analytics/features", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_training_jobs(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/analytics/training-jobs", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_backtests(self, client, auth_headers, mock_db_session):
        mock_db_session.execute = AsyncMock(return_value=_mock_scalars([]))
        resp = await client.get("/api/analytics/backtests", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_simulate(self, client, auth_headers):
        resp = await client.post(
            "/api/analytics/simulate",
            headers=auth_headers,
            json={
                "signal_hit_rate": 0.55,
                "avg_return_per_signal": 2.0,
                "avg_loss_per_signal": 1.5,
                "signals_per_period": 3,
                "num_periods": 20,
                "num_simulations": 50,
                "seed": 42,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "mean_final_value" in data
        assert "probability_of_profit" in data
        assert "sharpe_ratio_mean" in data

    @pytest.mark.asyncio
    async def test_simulate_auth_required(self, client):
        resp = await client.post("/api/analytics/simulate", json={})
        assert resp.status_code == 401
