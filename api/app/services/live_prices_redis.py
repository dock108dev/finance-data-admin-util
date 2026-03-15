"""Redis-backed live price caching for cross-exchange price data.

Equivalent to sports-data-admin's live_odds_redis.py.
Scraper writes live prices to Redis; API reads them for realtime display.
"""

import json
from datetime import datetime, timezone

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)

# ── Key Patterns ────────────────────────────────────────────────────────────

_SNAPSHOT_KEY = "live:price:{asset_class}:{asset_id}:{exchange}"
_ALL_PRICES_KEY = "live:prices:{asset_class}:{asset_id}"
_HISTORY_KEY = "live:price:history:{asset_id}:{exchange}"

_DEFAULT_TTL = 120  # 2 minutes


def _get_redis():
    """Get a Redis client using the configured URL."""
    import redis
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


# ── Snapshot API (write by scraper, read by API) ────────────────────────────

def write_live_price(
    asset_class: str,
    asset_id: int,
    exchange: str,
    price: float,
    bid: float | None = None,
    ask: float | None = None,
    volume_24h: float | None = None,
    ttl: int = _DEFAULT_TTL,
) -> None:
    """Write a live price snapshot to Redis."""
    r = _get_redis()
    key = _SNAPSHOT_KEY.format(
        asset_class=asset_class, asset_id=asset_id, exchange=exchange
    )
    data = {
        "price": price,
        "bid": bid,
        "ask": ask,
        "volume_24h": volume_24h,
        "exchange": exchange,
        "asset_id": asset_id,
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    r.setex(key, ttl, json.dumps(data))

    # Also append to history
    history_key = _HISTORY_KEY.format(asset_id=asset_id, exchange=exchange)
    r.lpush(history_key, json.dumps(data))
    r.ltrim(history_key, 0, 99)  # Keep last 100 entries
    r.expire(history_key, 3600)  # 1 hour TTL for history


def read_live_price(
    asset_class: str,
    asset_id: int,
    exchange: str,
) -> dict | None:
    """Read a single live price snapshot."""
    r = _get_redis()
    key = _SNAPSHOT_KEY.format(
        asset_class=asset_class, asset_id=asset_id, exchange=exchange
    )
    raw = r.get(key)
    if not raw:
        return None

    data = json.loads(raw)
    ttl = r.ttl(key)
    data["ttl_seconds_remaining"] = max(0, ttl)
    return data


def read_all_live_prices_for_asset(
    asset_class: str,
    asset_id: int,
) -> dict[str, dict]:
    """Read all exchange prices for an asset.

    Returns dict keyed by exchange name.
    """
    r = _get_redis()
    pattern = _SNAPSHOT_KEY.format(
        asset_class=asset_class, asset_id=asset_id, exchange="*"
    )
    result = {}
    for key in r.scan_iter(match=pattern, count=100):
        raw = r.get(key)
        if raw:
            data = json.loads(raw)
            exchange = data.get("exchange", "unknown")
            data["ttl_seconds_remaining"] = max(0, r.ttl(key))
            result[exchange] = data
    return result


def read_price_history(
    asset_id: int,
    exchange: str,
    count: int = 50,
) -> list[dict]:
    """Read recent price history for an asset on an exchange."""
    r = _get_redis()
    key = _HISTORY_KEY.format(asset_id=asset_id, exchange=exchange)
    raw_list = r.lrange(key, 0, count - 1)
    return [json.loads(raw) for raw in raw_list]


def discover_live_assets(
    asset_class: str | None = None,
) -> list[tuple[str, int]]:
    """Discover asset IDs with live price data.

    Returns list of (asset_class, asset_id) tuples.
    """
    r = _get_redis()
    pattern = "live:price:*"
    if asset_class:
        pattern = f"live:price:{asset_class}:*"

    seen = set()
    result = []
    for key in r.scan_iter(match=pattern, count=500):
        parts = key.split(":")
        if len(parts) >= 4:
            ac = parts[2]
            try:
                aid = int(parts[3])
                if (ac, aid) not in seen:
                    seen.add((ac, aid))
                    result.append((ac, aid))
            except (ValueError, IndexError):
                pass
    return result
