"""Asset class configuration — Single Source of Truth.

Equivalent to sports-data-admin's config_sports.py.
Every asset class (STOCKS, CRYPTO) has feature flags and polling intervals.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AssetClassConfig:
    """Configuration for an asset class (equivalent to LeagueConfig)."""

    code: str                              # "STOCKS", "CRYPTO"
    display_name: str
    # Feature flags
    prices_enabled: bool = True
    orderbook_enabled: bool = True
    social_enabled: bool = True
    onchain_enabled: bool = False          # Only crypto
    signals_enabled: bool = True
    analysis_enabled: bool = True
    # Polling intervals
    intraday_poll_minutes: int = 5
    exchange_sync_minutes: int = 1
    social_poll_minutes: int = 30
    onchain_poll_minutes: int = 15
    signal_poll_minutes: int = 15
    # Market hours (UTC)
    market_open_utc: str = "14:30"         # 9:30 AM ET
    market_close_utc: str = "21:00"        # 4:00 PM ET
    is_24h: bool = False                   # Crypto = True
    # Session defaults
    pregame_window_hours: int = 1          # Pre-market analysis
    postgame_window_hours: int = 2         # After-hours wrap
    # Exchanges to track (equiv. to sportsbooks)
    default_exchanges: tuple[str, ...] = ()


STOCKS_CONFIG = AssetClassConfig(
    code="STOCKS",
    display_name="US Equities",
    prices_enabled=True,
    orderbook_enabled=True,
    social_enabled=True,
    onchain_enabled=False,
    signals_enabled=True,
    analysis_enabled=True,
    intraday_poll_minutes=5,
    exchange_sync_minutes=1,
    market_open_utc="14:30",
    market_close_utc="21:00",
    is_24h=False,
    default_exchanges=("NYSE", "NASDAQ", "CBOE"),
)

CRYPTO_CONFIG = AssetClassConfig(
    code="CRYPTO",
    display_name="Cryptocurrency",
    prices_enabled=True,
    orderbook_enabled=True,
    social_enabled=True,
    onchain_enabled=True,
    signals_enabled=True,
    analysis_enabled=True,
    intraday_poll_minutes=1,
    exchange_sync_minutes=1,
    market_open_utc="00:00",
    market_close_utc="23:59",
    is_24h=True,
    onchain_poll_minutes=15,
    default_exchanges=("Binance", "Coinbase", "Kraken", "Bybit", "OKX"),
)


# ── SSOT Registry ────────────────────────────────────────────────────────────
ASSET_CLASS_CONFIG: dict[str, AssetClassConfig] = {
    "STOCKS": STOCKS_CONFIG,
    "CRYPTO": CRYPTO_CONFIG,
}


def get_enabled_asset_classes() -> list[AssetClassConfig]:
    """Return all asset classes with prices enabled."""
    return [c for c in ASSET_CLASS_CONFIG.values() if c.prices_enabled]
