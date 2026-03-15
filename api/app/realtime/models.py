"""Realtime event models and channel validation.

Equivalent to sports-data-admin's realtime/models.py.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any


# ── Channel Patterns ────────────────────────────────────────────────────────

# Valid channel formats:
#   prices:{asset_class}        — e.g. prices:CRYPTO, prices:STOCKS
#   asset:{id}:price            — e.g. asset:42:price
#   asset:{id}:signals          — e.g. asset:42:signals
#   signals:alpha               — all alpha signal updates
#   sessions:{asset_class}:{date} — session updates for a date

CHANNEL_PATTERNS = [
    re.compile(r"^prices:(CRYPTO|STOCKS)$"),
    re.compile(r"^asset:(\d+):price$"),
    re.compile(r"^asset:(\d+):signals$"),
    re.compile(r"^signals:alpha$"),
    re.compile(r"^sessions:(CRYPTO|STOCKS):(\d{4}-\d{2}-\d{2})$"),
]


def is_valid_channel(channel: str) -> bool:
    """Check if a channel string matches any known pattern."""
    return any(p.match(channel) for p in CHANNEL_PATTERNS)


def parse_channel(channel: str) -> dict[str, str]:
    """Extract components from a channel string.

    Returns dict with keys like 'type', 'asset_class', 'asset_id', 'date'.
    """
    parts = channel.split(":")

    if len(parts) == 2 and parts[0] == "prices":
        return {"type": "prices", "asset_class": parts[1]}
    elif len(parts) == 3 and parts[0] == "asset" and parts[2] == "price":
        return {"type": "asset_price", "asset_id": parts[1]}
    elif len(parts) == 3 and parts[0] == "asset" and parts[2] == "signals":
        return {"type": "asset_signals", "asset_id": parts[1]}
    elif channel == "signals:alpha":
        return {"type": "alpha_signals"}
    elif len(parts) == 3 and parts[0] == "sessions":
        return {"type": "sessions", "asset_class": parts[1], "date": parts[2]}
    return {"type": "unknown"}


# ── Event Envelope ──────────────────────────────────────────────────────────

@dataclass
class RealtimeEvent:
    """Server → client event envelope.

    Equivalent to sports-data-admin's RealtimeEvent.
    """

    type: str               # "price_update", "signal_alert", "session_update"
    channel: str
    seq: int
    payload: dict[str, Any] = field(default_factory=dict)
    boot_epoch: int = 0
    ts: int = field(default_factory=lambda: int(time.time() * 1000))

    def to_dict(self) -> dict[str, Any]:
        """Flatten into wire format — payload keys merged at top level."""
        result = {
            "type": self.type,
            "channel": self.channel,
            "seq": self.seq,
            "boot_epoch": self.boot_epoch,
            "ts": self.ts,
        }
        result.update(self.payload)
        return result
