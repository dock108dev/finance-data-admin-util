"""Alpha signal strategy configuration — equivalent to ev_config.py.

Defines which signal strategies are enabled for which asset class
and market type. Controls confidence tiers, thresholds, and reference
exchange selection.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalStrategyConfig:
    """Configuration for an alpha signal strategy.

    Equivalent to sports-data-admin's EVStrategyConfig.
    """
    strategy_name: str
    eligible_reference_exchanges: tuple[str, ...]
    min_qualifying_exchanges: int
    max_reference_staleness_seconds: int
    confidence_tier: str                 # "HIGH", "MEDIUM", "LOW"
    min_spread_threshold_pct: float      # Minimum % to flag as opportunity
    max_spread_divergence_pct: float     # Max divergence before "outlier" flag
    fee_estimate_pct: float              # Estimated round-trip trading fees
    allow_low_liquidity: bool = False


# ── Confidence Tiers ─────────────────────────────────────────────────────────
#
# HIGH   — Highly liquid market, tight spreads, reference reliable
#          (e.g., BTC/ETH spot on Binance, AAPL on NYSE)
# MEDIUM — Moderate liquidity, reference generally reliable
#          (e.g., mid-cap alts, small-cap stocks)
# LOW    — Thin liquidity, use signals directionally only
#          (e.g., micro-cap tokens, OTC stocks)

# ── Strategy Definitions ────────────────────────────────────────────────────

_CRYPTO_SPOT_LARGE_CAP = SignalStrategyConfig(
    strategy_name="crypto_spot_large_cap",
    eligible_reference_exchanges=("Binance",),
    min_qualifying_exchanges=4,
    max_reference_staleness_seconds=60,       # 1 minute
    confidence_tier="HIGH",
    min_spread_threshold_pct=0.3,
    max_spread_divergence_pct=5.0,
    fee_estimate_pct=0.2,
)

_CRYPTO_SPOT_MID_CAP = SignalStrategyConfig(
    strategy_name="crypto_spot_mid_cap",
    eligible_reference_exchanges=("Binance", "Coinbase"),
    min_qualifying_exchanges=3,
    max_reference_staleness_seconds=120,      # 2 minutes
    confidence_tier="MEDIUM",
    min_spread_threshold_pct=0.5,
    max_spread_divergence_pct=8.0,
    fee_estimate_pct=0.3,
)

_CRYPTO_SPOT_SMALL_CAP = SignalStrategyConfig(
    strategy_name="crypto_spot_small_cap",
    eligible_reference_exchanges=("Binance", "Coinbase", "KuCoin"),
    min_qualifying_exchanges=2,
    max_reference_staleness_seconds=300,      # 5 minutes
    confidence_tier="LOW",
    min_spread_threshold_pct=1.0,
    max_spread_divergence_pct=15.0,
    fee_estimate_pct=0.5,
    allow_low_liquidity=True,
)

_STOCK_LARGE_CAP = SignalStrategyConfig(
    strategy_name="stock_large_cap",
    eligible_reference_exchanges=("NYSE", "NASDAQ"),
    min_qualifying_exchanges=2,
    max_reference_staleness_seconds=300,      # 5 minutes
    confidence_tier="HIGH",
    min_spread_threshold_pct=0.05,
    max_spread_divergence_pct=1.0,
    fee_estimate_pct=0.02,
)

_STOCK_MID_CAP = SignalStrategyConfig(
    strategy_name="stock_mid_cap",
    eligible_reference_exchanges=("NYSE", "NASDAQ"),
    min_qualifying_exchanges=2,
    max_reference_staleness_seconds=600,      # 10 minutes
    confidence_tier="MEDIUM",
    min_spread_threshold_pct=0.1,
    max_spread_divergence_pct=3.0,
    fee_estimate_pct=0.05,
)


# ── Strategy Map ────────────────────────────────────────────────────────────
# (asset_class, market_type, cap_tier) → SignalStrategyConfig | None

STRATEGY_MAP: dict[tuple[str, str, str], SignalStrategyConfig | None] = {
    # Crypto
    ("CRYPTO", "spot", "large"):   _CRYPTO_SPOT_LARGE_CAP,
    ("CRYPTO", "spot", "mid"):     _CRYPTO_SPOT_MID_CAP,
    ("CRYPTO", "spot", "small"):   _CRYPTO_SPOT_SMALL_CAP,
    ("CRYPTO", "futures", "large"): None,   # Disabled — complex hedging needed
    ("CRYPTO", "futures", "mid"):   None,
    ("CRYPTO", "futures", "small"): None,
    # Stocks
    ("STOCKS", "spot", "large"):   _STOCK_LARGE_CAP,
    ("STOCKS", "spot", "mid"):     _STOCK_MID_CAP,
    ("STOCKS", "spot", "small"):   None,    # Disabled — insufficient data
    ("STOCKS", "options", "large"): None,   # Disabled — separate pipeline needed
    ("STOCKS", "options", "mid"):   None,
}


def get_strategy(
    asset_class: str,
    market_type: str,
    market_cap: float | None = None,
) -> SignalStrategyConfig | None:
    """Resolve the strategy for an asset based on class, market, and cap tier."""
    tier = _classify_cap_tier(asset_class, market_cap)
    return STRATEGY_MAP.get((asset_class, market_type, tier))


def _classify_cap_tier(asset_class: str, market_cap: float | None) -> str:
    """Classify an asset into cap tiers based on market cap."""
    if market_cap is None:
        return "mid"  # Default to mid if unknown

    if asset_class == "CRYPTO":
        if market_cap >= 10_000_000_000:    # $10B+
            return "large"
        elif market_cap >= 500_000_000:     # $500M+
            return "mid"
        else:
            return "small"
    else:  # STOCKS
        if market_cap >= 10_000_000_000:    # $10B+
            return "large"
        elif market_cap >= 2_000_000_000:   # $2B+
            return "mid"
        else:
            return "small"


# ── Signal Disabled Reasons ──────────────────────────────────────────────────
#
# | Reason                  | Cause                                    |
# |-------------------------|------------------------------------------|
# | no_strategy             | No configured strategy for this combo    |
# | reference_missing       | Reference exchange not present           |
# | reference_stale         | Reference data too old                   |
# | insufficient_exchanges  | < min qualifying exchanges               |
# | spread_outlier          | Spread exceeds max divergence threshold  |
# | low_liquidity           | Volume below actionable threshold        |
# | high_fees               | Estimated fees exceed potential profit   |
