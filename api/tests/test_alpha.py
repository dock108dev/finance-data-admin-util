"""Tests for alpha signal computation — equivalent to sports test_ev.py."""

import pytest
from datetime import datetime, timedelta, timezone

from app.services.alpha import (
    ExchangeQuote,
    compute_arbitrage,
    compute_bollinger_bands,
    compute_macd,
    compute_rsi,
    compute_sentiment_divergence,
    compute_technical_signals,
    evaluate_signal_eligibility,
    CRYPTO_ARB_STRATEGY,
)


class TestEvaluateSignalEligibility:
    """Test the 4-check eligibility gate."""

    def test_no_strategy_returns_ineligible(self):
        result = evaluate_signal_eligibility("CRYPTO", "options", [])
        assert not result.eligible
        assert result.reason == "no_strategy"

    def test_missing_reference_returns_ineligible(self):
        quotes = [
            ExchangeQuote("Coinbase", 65000, observed_at=datetime.now(timezone.utc)),
            ExchangeQuote("Kraken", 65100, observed_at=datetime.now(timezone.utc)),
        ]
        result = evaluate_signal_eligibility("CRYPTO", "spot", quotes)
        assert not result.eligible
        assert result.reason == "reference_missing"

    def test_stale_reference_returns_ineligible(self):
        now = datetime.utcnow()
        old_time = now - timedelta(days=365)
        quotes = [
            ExchangeQuote("Binance", 65000, observed_at=old_time),
            ExchangeQuote("Coinbase", 65100, observed_at=now),
        ]
        result = evaluate_signal_eligibility("CRYPTO", "spot", quotes, now=now)
        assert not result.eligible
        assert result.reason == "reference_stale"

    def test_insufficient_exchanges_returns_ineligible(self):
        now = datetime.utcnow()
        quotes = [
            ExchangeQuote("Binance", 65000, observed_at=now),
            ExchangeQuote("Coinbase", 65100, observed_at=now),
        ]
        result = evaluate_signal_eligibility("CRYPTO", "spot", quotes, now=now)
        assert not result.eligible
        assert result.reason == "insufficient_exchanges"

    def test_valid_quotes_returns_eligible(self):
        now = datetime.utcnow()
        quotes = [
            ExchangeQuote("Binance", 65000, observed_at=now),
            ExchangeQuote("Coinbase", 65100, observed_at=now),
            ExchangeQuote("Kraken", 65050, observed_at=now),
            ExchangeQuote("Bybit", 65200, observed_at=now),
        ]
        result = evaluate_signal_eligibility("CRYPTO", "spot", quotes, now=now)
        assert result.eligible
        assert result.strategy_config is not None


class TestComputeArbitrage:
    """Test cross-exchange arbitrage computation."""

    def test_computes_spread_correctly(self):
        quotes = [
            ExchangeQuote("Binance", 65000),
            ExchangeQuote("Coinbase", 65650),   # +1.0%
            ExchangeQuote("Kraken", 64350),     # -1.0%
        ]
        result = compute_arbitrage(quotes, CRYPTO_ARB_STRATEGY)
        assert result.reference_exchange == "Binance"
        assert result.reference_price == 65000
        assert len(result.opportunities) == 2

    def test_identifies_actionable_opportunities(self):
        quotes = [
            ExchangeQuote("Binance", 65000),
            ExchangeQuote("Coinbase", 66300),   # +2.0% → after 0.2% fees = +1.8%
        ]
        result = compute_arbitrage(quotes, CRYPTO_ARB_STRATEGY)
        assert result.opportunities[0].is_actionable
        assert result.opportunities[0].estimated_profit_pct > 0


class TestTechnicalIndicators:
    """Test RSI, MACD, Bollinger Bands."""

    def test_rsi_oversold(self):
        # Simulate declining prices
        closes = [100 - i * 0.5 for i in range(20)]
        rsi = compute_rsi(closes)
        assert rsi is not None
        assert rsi < 50

    def test_rsi_insufficient_data(self):
        assert compute_rsi([100, 101, 102]) is None

    def test_macd_returns_tuple(self):
        closes = [100 + i * 0.1 for i in range(40)]
        result = compute_macd(closes)
        assert result is not None
        assert len(result) == 3

    def test_macd_insufficient_data(self):
        assert compute_macd([100, 101]) is None

    def test_bollinger_bands(self):
        closes = [100 + (i % 5) for i in range(25)]
        result = compute_bollinger_bands(closes)
        assert result is not None
        upper, middle, lower = result
        assert upper > middle > lower

    def test_bollinger_insufficient_data(self):
        assert compute_bollinger_bands([100, 101]) is None


class TestTechnicalSignals:
    """Test consolidated technical signal computation."""

    def test_returns_signals_for_sufficient_data(self):
        closes = [100 + i * 0.1 for i in range(40)]
        signals = compute_technical_signals(closes, current_price=104.0)
        assert len(signals) > 0

    def test_returns_empty_for_insufficient_data(self):
        signals = compute_technical_signals([100], current_price=100)
        assert len(signals) == 0


class TestSentimentDivergence:
    """Test sentiment vs. price divergence detection."""

    def test_bullish_divergence(self):
        # Price down, sentiment bullish
        result = compute_sentiment_divergence(
            price_change_pct=-5.0,
            sentiment_score=0.8,
        )
        assert result is not None
        assert result.signal == "BUY"

    def test_bearish_divergence(self):
        # Price up, sentiment bearish
        result = compute_sentiment_divergence(
            price_change_pct=5.0,
            sentiment_score=-0.8,
        )
        assert result is not None
        assert result.signal == "SELL"

    def test_no_divergence(self):
        # Price and sentiment aligned
        result = compute_sentiment_divergence(
            price_change_pct=3.0,
            sentiment_score=0.3,
        )
        assert result is None


class TestExcludedExchanges:
    def test_excluded_exchange_filtered_from_qualifying(self):
        from app.services.alpha import EXCLUDED_EXCHANGES
        now = datetime.utcnow()
        # Use 2 valid + 1 excluded + reference = only 2 qualifying (Binance is ref)
        quotes = [
            ExchangeQuote("Binance", 65000, observed_at=now),
            ExchangeQuote("Coinbase", 65100, observed_at=now),
            ExchangeQuote("Unknown DEX", 65200, observed_at=now),
        ]
        result = evaluate_signal_eligibility("CRYPTO", "spot", quotes, now=now)
        # Only 2 qualifying (Binance + Coinbase), need 3 → insufficient
        assert not result.eligible
        assert result.reason == "insufficient_exchanges"


class TestComputeArbitrageExtended:
    def test_fee_subtraction(self):
        quotes = [
            ExchangeQuote("Binance", 10000),
            ExchangeQuote("Coinbase", 10050),  # 0.5% spread
        ]
        result = compute_arbitrage(quotes, CRYPTO_ARB_STRATEGY)
        opp = result.opportunities[0]
        # 0.5% spread - 0.2% fees = 0.3% profit
        assert opp.estimated_profit_pct == pytest.approx(0.3, abs=0.01)

    def test_sort_order_by_spread(self):
        quotes = [
            ExchangeQuote("Binance", 10000),
            ExchangeQuote("Coinbase", 10100),   # 1.0%
            ExchangeQuote("Kraken", 10300),      # 3.0%
        ]
        result = compute_arbitrage(quotes, CRYPTO_ARB_STRATEGY)
        assert abs(result.opportunities[0].spread_pct) >= abs(result.opportunities[1].spread_pct)

    def test_excluded_exchange_not_in_opps(self):
        quotes = [
            ExchangeQuote("Binance", 10000),
            ExchangeQuote("Unknown DEX", 10500),
            ExchangeQuote("Coinbase", 10100),
        ]
        result = compute_arbitrage(quotes, CRYPTO_ARB_STRATEGY)
        exchanges = [o.exchange for o in result.opportunities]
        assert "Unknown DEX" not in exchanges


class TestRSIExtended:
    def test_rsi_overbought(self):
        # Simulate all gains
        closes = [100 + i * 2 for i in range(20)]
        rsi = compute_rsi(closes)
        assert rsi is not None
        assert rsi > 70

    def test_rsi_all_gains_is_100(self):
        # Pure monotonic increase → RSI = 100
        closes = [float(i) for i in range(1, 20)]
        rsi = compute_rsi(closes)
        assert rsi == 100.0


class TestMACDExtended:
    def test_macd_sell_signal_declining(self):
        # Declining prices → negative histogram
        closes = [200 - i * 0.3 for i in range(40)]
        result = compute_macd(closes)
        assert result is not None
        _, _, histogram = result
        assert histogram < 0


class TestBollingerExtended:
    def test_bb_price_above_upper_is_sell(self):
        closes = [100 + (i % 3) for i in range(25)]
        result = compute_bollinger_bands(closes)
        upper, _, _ = result
        signals = compute_technical_signals(closes, current_price=upper + 5)
        bb_signals = [s for s in signals if s.indicator == "BB"]
        assert len(bb_signals) == 1
        assert bb_signals[0].signal == "SELL"
