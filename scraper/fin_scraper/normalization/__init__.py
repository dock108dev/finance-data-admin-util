"""Data normalization layer — standardize financial data across sources.

Handles currency conversion, volume normalization, timestamp alignment,
and ticker mapping across exchanges.
"""

from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def normalize_price(price: float | str | None, currency: str = "USD") -> float | None:
    """Normalize a price value to float, handling string inputs."""
    if price is None:
        return None
    try:
        return float(price)
    except (ValueError, TypeError):
        return None


def normalize_volume(volume: float | str | None) -> float | None:
    """Normalize volume — handle K/M/B suffixes."""
    if volume is None:
        return None
    if isinstance(volume, str):
        volume = volume.strip().upper()
        multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
        for suffix, mult in multipliers.items():
            if volume.endswith(suffix):
                try:
                    return float(volume[:-1]) * mult
                except ValueError:
                    return None
        try:
            return float(volume.replace(",", ""))
        except ValueError:
            return None
    return float(volume)


def normalize_timestamp(ts: Any, source_tz: str | None = None) -> datetime | None:
    """Normalize various timestamp formats to UTC datetime."""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    if isinstance(ts, (int, float)):
        if ts > 1e12:
            ts = ts / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(ts, str):
        for fmt in [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]:
            try:
                dt = datetime.strptime(ts, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            pass
    return None


def normalize_ticker(ticker: str, exchange: str | None = None) -> str:
    """Normalize ticker symbols across exchanges."""
    ticker = ticker.strip().upper()
    for suffix in ["USDT", "BUSD", "USDC", "-USD", "/USD", ".US", "USD"]:
        if ticker.endswith(suffix):
            ticker = ticker[: -len(suffix)]
            break
    return ticker


def normalize_candle(raw: dict, source: str) -> dict:
    """Normalize a raw candle from any source to standard format."""
    return {
        "timestamp": normalize_timestamp(
            raw.get("timestamp") or raw.get("t") or raw.get("date")
        ),
        "open": normalize_price(raw.get("open") or raw.get("o")),
        "high": normalize_price(raw.get("high") or raw.get("h")),
        "low": normalize_price(raw.get("low") or raw.get("l")),
        "close": normalize_price(raw.get("close") or raw.get("c")),
        "volume": normalize_volume(raw.get("volume") or raw.get("v")),
        "source": source,
    }
