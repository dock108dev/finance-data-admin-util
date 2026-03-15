"""Order book snapshot management — capture and persist order book data."""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class OrderBookLevel:
    """Single price level in an order book."""
    price: float
    quantity: float
    side: str  # "bid" or "ask"


@dataclass
class OrderBookSnapshot:
    """Point-in-time snapshot of an order book."""
    asset_id: int
    exchange: str
    timestamp: datetime
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    mid_price: float | None = None
    spread: float | None = None
    spread_pct: float | None = None

    def __post_init__(self):
        if self.bids and self.asks:
            best_bid = max(self.bids, key=lambda l: l.price).price
            best_ask = min(self.asks, key=lambda l: l.price).price
            self.mid_price = (best_bid + best_ask) / 2
            self.spread = best_ask - best_bid
            self.spread_pct = (self.spread / self.mid_price * 100) if self.mid_price > 0 else 0


def create_snapshot(
    asset_id: int,
    exchange: str,
    bids: list[tuple[float, float]],
    asks: list[tuple[float, float]],
) -> OrderBookSnapshot:
    """Create an order book snapshot from raw bid/ask data."""
    bid_levels = [OrderBookLevel(p, q, "bid") for p, q in bids]
    ask_levels = [OrderBookLevel(p, q, "ask") for p, q in asks]
    return OrderBookSnapshot(
        asset_id=asset_id,
        exchange=exchange,
        timestamp=datetime.now(timezone.utc),
        bids=bid_levels,
        asks=ask_levels,
    )


def compute_depth(snapshot: OrderBookSnapshot, pct_from_mid: float = 1.0) -> dict:
    """Compute order book depth within a percentage range of mid price."""
    if not snapshot.mid_price:
        return {"bid_depth": 0, "ask_depth": 0, "imbalance": 0}

    lower = snapshot.mid_price * (1 - pct_from_mid / 100)
    upper = snapshot.mid_price * (1 + pct_from_mid / 100)

    bid_depth = sum(l.price * l.quantity for l in snapshot.bids if l.price >= lower)
    ask_depth = sum(l.price * l.quantity for l in snapshot.asks if l.price <= upper)
    total = bid_depth + ask_depth
    imbalance = (bid_depth - ask_depth) / total if total > 0 else 0

    return {
        "bid_depth": round(bid_depth, 2),
        "ask_depth": round(ask_depth, 2),
        "imbalance": round(imbalance, 4),
    }
