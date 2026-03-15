"""Tests for alpha signal strategy configuration."""

import pytest

from app.services.alpha_config import (
    STRATEGY_MAP,
    SignalStrategyConfig,
    _classify_cap_tier,
    get_strategy,
)


class TestClassifyCapTier:
    # Crypto boundaries
    def test_crypto_large_cap(self):
        assert _classify_cap_tier("CRYPTO", 10_000_000_000) == "large"

    def test_crypto_large_cap_above(self):
        assert _classify_cap_tier("CRYPTO", 50_000_000_000) == "large"

    def test_crypto_mid_cap(self):
        assert _classify_cap_tier("CRYPTO", 500_000_000) == "mid"

    def test_crypto_mid_cap_above(self):
        assert _classify_cap_tier("CRYPTO", 5_000_000_000) == "mid"

    def test_crypto_small_cap(self):
        assert _classify_cap_tier("CRYPTO", 100_000_000) == "small"

    def test_crypto_small_cap_near_zero(self):
        assert _classify_cap_tier("CRYPTO", 1000) == "small"

    # Stock boundaries
    def test_stock_large_cap(self):
        assert _classify_cap_tier("STOCKS", 10_000_000_000) == "large"

    def test_stock_mid_cap(self):
        assert _classify_cap_tier("STOCKS", 2_000_000_000) == "mid"

    def test_stock_small_cap(self):
        assert _classify_cap_tier("STOCKS", 500_000_000) == "small"

    # None defaults to mid
    def test_none_returns_mid(self):
        assert _classify_cap_tier("CRYPTO", None) == "mid"

    def test_none_returns_mid_stocks(self):
        assert _classify_cap_tier("STOCKS", None) == "mid"


class TestGetStrategy:
    def test_crypto_spot_large_returns_config(self):
        result = get_strategy("CRYPTO", "spot", market_cap=50e9)
        assert result is not None
        assert isinstance(result, SignalStrategyConfig)
        assert result.strategy_name == "crypto_spot_large_cap"

    def test_crypto_spot_mid_returns_config(self):
        result = get_strategy("CRYPTO", "spot", market_cap=1e9)
        assert result is not None
        assert result.strategy_name == "crypto_spot_mid_cap"

    def test_crypto_spot_small_returns_config(self):
        result = get_strategy("CRYPTO", "spot", market_cap=100e6)
        assert result is not None
        assert result.strategy_name == "crypto_spot_small_cap"

    def test_crypto_futures_disabled(self):
        result = get_strategy("CRYPTO", "futures", market_cap=50e9)
        assert result is None

    def test_stock_spot_large_returns_config(self):
        result = get_strategy("STOCKS", "spot", market_cap=50e9)
        assert result is not None
        assert result.strategy_name == "stock_large_cap"

    def test_stock_spot_small_disabled(self):
        result = get_strategy("STOCKS", "spot", market_cap=100e6)
        assert result is None

    def test_stock_options_disabled(self):
        result = get_strategy("STOCKS", "options", market_cap=50e9)
        assert result is None

    def test_unknown_combo_returns_none(self):
        result = get_strategy("FOREX", "spot", market_cap=1e9)
        assert result is None

    def test_none_market_cap_defaults_to_mid(self):
        result = get_strategy("CRYPTO", "spot")
        assert result is not None
        assert result.strategy_name == "crypto_spot_mid_cap"


class TestStrategyConfigValues:
    def test_crypto_large_has_high_confidence(self):
        s = get_strategy("CRYPTO", "spot", market_cap=50e9)
        assert s.confidence_tier == "HIGH"

    def test_crypto_small_allows_low_liquidity(self):
        s = get_strategy("CRYPTO", "spot", market_cap=100e6)
        assert s.allow_low_liquidity is True

    def test_stock_large_low_fee_estimate(self):
        s = get_strategy("STOCKS", "spot", market_cap=50e9)
        assert s.fee_estimate_pct < 0.1
