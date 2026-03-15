"""In-memory pub/sub manager with connection registry.

Equivalent to sports-data-admin's realtime/manager.py.
Manages WebSocket and SSE connections, channel subscriptions,
and event fan-out.
"""

import asyncio
import json
import time
from collections import defaultdict
from typing import Any, Callable, Coroutine, Protocol

import structlog

from app.realtime.models import RealtimeEvent

logger = structlog.get_logger(__name__)

# ── Constants ───────────────────────────────────────────────────────────────

MAX_CHANNELS_PER_CONNECTION = 50
SSE_QUEUE_MAX = 200
WS_SEND_TIMEOUT_S = 2.0

OnFirstSubscriberCallback = Callable[[str], Coroutine[Any, Any, None]]


# ── Connection Protocols ────────────────────────────────────────────────────

class Connection(Protocol):
    """Protocol for WebSocket and SSE connections."""

    @property
    def id(self) -> str: ...

    async def send_event(self, data: str) -> None: ...


class WSConnection:
    """Wraps a Starlette WebSocket for the manager."""

    def __init__(self, websocket):
        self._ws = websocket
        self._id = f"ws-{id(websocket)}"

    @property
    def id(self) -> str:
        return self._id

    async def send_event(self, data: str) -> None:
        try:
            await asyncio.wait_for(
                self._ws.send_text(data),
                timeout=WS_SEND_TIMEOUT_S,
            )
        except (asyncio.TimeoutError, Exception):
            raise ConnectionError(f"WS send failed for {self._id}")


class SSEConnection:
    """Queue-based connection for Server-Sent Events."""

    def __init__(self):
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=SSE_QUEUE_MAX)
        self._id = f"sse-{id(self)}"

    @property
    def id(self) -> str:
        return self._id

    @property
    def queue(self) -> asyncio.Queue[str]:
        return self._queue

    async def send_event(self, data: str) -> None:
        try:
            self._queue.put_nowait(data)
        except asyncio.QueueFull:
            raise ConnectionError(f"SSE queue overflow for {self._id}")


# ── Realtime Manager ────────────────────────────────────────────────────────

class RealtimeManager:
    """Central pub/sub manager for realtime connections.

    Thread-safe for asyncio. Single instance per process.
    """

    def __init__(self):
        self._channel_subscribers: dict[str, set[str]] = defaultdict(set)
        self._connections: dict[str, Connection] = {}
        self._conn_channels: dict[str, set[str]] = defaultdict(set)
        self._seq: dict[str, int] = defaultdict(int)
        self._publish_count = 0
        self._error_count = 0
        self.boot_epoch = int(time.time())
        self._on_first_subscriber: OnFirstSubscriberCallback | None = None

    def set_on_first_subscriber(self, callback: OnFirstSubscriberCallback) -> None:
        """Register callback for when a channel gets its first subscriber."""
        self._on_first_subscriber = callback

    def subscribe(self, conn: Connection, channel: str) -> bool:
        """Subscribe a connection to a channel.

        Returns True if subscribed, False if at channel limit.
        """
        if len(self._conn_channels[conn.id]) >= MAX_CHANNELS_PER_CONNECTION:
            return False

        was_empty = len(self._channel_subscribers[channel]) == 0
        self._connections[conn.id] = conn
        self._channel_subscribers[channel].add(conn.id)
        self._conn_channels[conn.id].add(channel)

        if was_empty and self._on_first_subscriber:
            asyncio.create_task(self._on_first_subscriber(channel))

        return True

    def unsubscribe(self, conn: Connection, channel: str) -> None:
        """Remove a connection from a channel."""
        self._channel_subscribers[channel].discard(conn.id)
        self._conn_channels[conn.id].discard(channel)

        if not self._channel_subscribers[channel]:
            del self._channel_subscribers[channel]

    def disconnect(self, conn: Connection) -> None:
        """Remove a connection from all channels."""
        channels = list(self._conn_channels.get(conn.id, []))
        for ch in channels:
            self._channel_subscribers[ch].discard(conn.id)
            if not self._channel_subscribers[ch]:
                del self._channel_subscribers[ch]

        self._conn_channels.pop(conn.id, None)
        self._connections.pop(conn.id, None)

    async def publish(self, channel: str, event_type: str, payload: dict) -> int:
        """Publish an event to all subscribers of a channel.

        Returns number of connections that received the event.
        Non-blocking: drops slow subscribers.
        """
        subscriber_ids = self._channel_subscribers.get(channel, set())
        if not subscriber_ids:
            return 0

        self._seq[channel] += 1
        event = RealtimeEvent(
            type=event_type,
            channel=channel,
            seq=self._seq[channel],
            payload=payload,
            boot_epoch=self.boot_epoch,
        )
        data = json.dumps(event.to_dict())

        sent = 0
        dead_conns: list[str] = []

        for conn_id in list(subscriber_ids):
            conn = self._connections.get(conn_id)
            if conn is None:
                dead_conns.append(conn_id)
                continue

            try:
                await conn.send_event(data)
                sent += 1
            except ConnectionError:
                dead_conns.append(conn_id)
                self._error_count += 1
            except Exception:
                dead_conns.append(conn_id)
                self._error_count += 1

        # Clean up dead connections
        for conn_id in dead_conns:
            conn = self._connections.get(conn_id)
            if conn:
                self.disconnect(conn)

        self._publish_count += 1
        return sent

    def has_subscribers(self, channel: str) -> bool:
        """Check if a channel has any active subscribers."""
        return bool(self._channel_subscribers.get(channel))

    def active_channels(self) -> set[str]:
        """Return all channels with at least one subscriber."""
        return set(self._channel_subscribers.keys())

    def status(self) -> dict[str, Any]:
        """Return manager status for diagnostics."""
        channels_detail = {
            ch: len(subs) for ch, subs in self._channel_subscribers.items()
        }
        return {
            "boot_epoch": self.boot_epoch,
            "total_connections": len(self._connections),
            "total_channels": len(self._channel_subscribers),
            "channels": channels_detail,
            "publish_count": self._publish_count,
            "error_count": self._error_count,
        }


# ── Singleton ───────────────────────────────────────────────────────────────

realtime_manager = RealtimeManager()
