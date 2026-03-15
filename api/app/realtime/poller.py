"""Database poller — emits realtime events from DB changes.

Equivalent to sports-data-admin's realtime/poller.py.
Background asyncio tasks that poll for price updates, signal alerts,
and session changes, then publish to connected clients.
"""

import asyncio
from datetime import datetime, timezone

import structlog

from app.realtime.manager import realtime_manager

logger = structlog.get_logger(__name__)

# ── Poll Intervals ──────────────────────────────────────────────────────────

POLL_PRICES_INTERVAL_S = 2
POLL_SIGNALS_INTERVAL_S = 5
POLL_SESSIONS_INTERVAL_S = 10


class DBPoller:
    """Background polling engine for realtime event emission.

    Polls the database for changes and publishes events to
    subscribers via the RealtimeManager.
    """

    def __init__(self):
        self._tasks: list[asyncio.Task] = []
        self._running = False
        self._stats = {
            "poll_count": {"prices": 0, "signals": 0, "sessions": 0},
            "last_poll_duration_ms": {"prices": 0, "signals": 0, "sessions": 0},
            "last_poll_at": {"prices": None, "signals": None, "sessions": None},
        }
        # Track last-seen timestamps for deduplication
        self._last_price_at: datetime | None = None
        self._last_signal_at: datetime | None = None
        self._last_session_at: datetime | None = None

    def start(self) -> None:
        """Start all polling loops as background tasks."""
        if self._running:
            return

        self._running = True
        self._tasks = [
            asyncio.create_task(self._poll_prices_loop()),
            asyncio.create_task(self._poll_signals_loop()),
            asyncio.create_task(self._poll_sessions_loop()),
        ]
        logger.info("poller.started", loops=len(self._tasks))

    async def stop(self) -> None:
        """Gracefully cancel all polling loops."""
        self._running = False
        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks = []
        logger.info("poller.stopped")

    def stats(self) -> dict:
        """Return polling statistics for diagnostics."""
        return dict(self._stats)

    # ── Polling Loops ───────────────────────────────────────────────────

    async def _poll_prices_loop(self) -> None:
        """Poll for exchange price updates."""
        try:
            while self._running:
                await asyncio.sleep(POLL_PRICES_INTERVAL_S)

                # Only poll if someone is listening to price channels
                active = realtime_manager.active_channels()
                price_channels = [
                    ch for ch in active
                    if ch.startswith("prices:") or (":price" in ch)
                ]
                if not price_channels:
                    continue

                start = asyncio.get_event_loop().time()

                try:
                    await self._poll_prices(price_channels)
                except Exception as e:
                    logger.error("poller.prices_error", error=str(e))

                elapsed = (asyncio.get_event_loop().time() - start) * 1000
                self._stats["poll_count"]["prices"] += 1
                self._stats["last_poll_duration_ms"]["prices"] = round(elapsed, 1)
                self._stats["last_poll_at"]["prices"] = datetime.now(timezone.utc).isoformat()

        except asyncio.CancelledError:
            pass

    async def _poll_signals_loop(self) -> None:
        """Poll for new alpha signals."""
        try:
            while self._running:
                await asyncio.sleep(POLL_SIGNALS_INTERVAL_S)

                active = realtime_manager.active_channels()
                signal_channels = [
                    ch for ch in active
                    if ch.startswith("signals:") or ":signals" in ch
                ]
                if not signal_channels:
                    continue

                start = asyncio.get_event_loop().time()

                try:
                    await self._poll_signals(signal_channels)
                except Exception as e:
                    logger.error("poller.signals_error", error=str(e))

                elapsed = (asyncio.get_event_loop().time() - start) * 1000
                self._stats["poll_count"]["signals"] += 1
                self._stats["last_poll_duration_ms"]["signals"] = round(elapsed, 1)
                self._stats["last_poll_at"]["signals"] = datetime.now(timezone.utc).isoformat()

        except asyncio.CancelledError:
            pass

    async def _poll_sessions_loop(self) -> None:
        """Poll for session status changes."""
        try:
            while self._running:
                await asyncio.sleep(POLL_SESSIONS_INTERVAL_S)

                active = realtime_manager.active_channels()
                session_channels = [
                    ch for ch in active if ch.startswith("sessions:")
                ]
                if not session_channels:
                    continue

                start = asyncio.get_event_loop().time()

                try:
                    await self._poll_sessions(session_channels)
                except Exception as e:
                    logger.error("poller.sessions_error", error=str(e))

                elapsed = (asyncio.get_event_loop().time() - start) * 1000
                self._stats["poll_count"]["sessions"] += 1
                self._stats["last_poll_duration_ms"]["sessions"] = round(elapsed, 1)
                self._stats["last_poll_at"]["sessions"] = datetime.now(timezone.utc).isoformat()

        except asyncio.CancelledError:
            pass

    # ── Poll Implementations ────────────────────────────────────────────

    async def _poll_prices(self, channels: list[str]) -> None:
        """Fetch recent price changes and publish to subscribers.

        In production, this queries fin_exchange_prices or uses
        Redis-cached live prices. For now, publishes from
        the latest exchange_prices rows updated since last poll.
        """
        from app.db.session import get_db

        try:
            from sqlalchemy import text

            async for db in get_db():
                # Get prices updated since last poll
                since = self._last_price_at or datetime.now(timezone.utc)
                result = await db.execute(
                    text("""
                        SELECT ep.asset_id, a.ticker, ep.exchange, ep.price,
                               ep.bid, ep.ask, ep.volume_24h, ep.observed_at,
                               ac.code as asset_class
                        FROM fin_exchange_prices ep
                        JOIN fin_assets a ON a.id = ep.asset_id
                        JOIN fin_asset_classes ac ON ac.id = a.asset_class_id
                        WHERE ep.observed_at > :since
                        ORDER BY ep.observed_at DESC
                        LIMIT 100
                    """),
                    {"since": since},
                )
                rows = result.mappings().all()

                for row in rows:
                    # Publish to asset-specific channel
                    asset_channel = f"asset:{row['asset_id']}:price"
                    if realtime_manager.has_subscribers(asset_channel):
                        await realtime_manager.publish(
                            asset_channel,
                            "price_update",
                            {
                                "asset_id": row["asset_id"],
                                "ticker": row["ticker"],
                                "exchange": row["exchange"],
                                "price": row["price"],
                                "bid": row["bid"],
                                "ask": row["ask"],
                                "volume_24h": row["volume_24h"],
                            },
                        )

                    # Publish to asset-class channel
                    class_channel = f"prices:{row['asset_class']}"
                    if realtime_manager.has_subscribers(class_channel):
                        await realtime_manager.publish(
                            class_channel,
                            "price_update",
                            {
                                "asset_id": row["asset_id"],
                                "ticker": row["ticker"],
                                "exchange": row["exchange"],
                                "price": row["price"],
                            },
                        )

                if rows:
                    self._last_price_at = rows[0]["observed_at"]
                break  # Only need one iteration of the async generator

        except Exception as e:
            logger.warning("poller.prices_query_failed", error=str(e))

    async def _poll_signals(self, channels: list[str]) -> None:
        """Fetch new alpha signals and publish to subscribers."""
        try:
            from sqlalchemy import text

            async for db in get_db():
                since = self._last_signal_at or datetime.now(timezone.utc)
                result = await db.execute(
                    text("""
                        SELECT s.id, s.asset_id, s.signal_type, s.direction,
                               s.strength, s.confidence_tier, s.trigger_price,
                               s.detected_at, a.ticker
                        FROM fin_alpha_signals s
                        JOIN fin_assets a ON a.id = s.asset_id
                        WHERE s.detected_at > :since
                        ORDER BY s.detected_at DESC
                        LIMIT 50
                    """),
                    {"since": since},
                )
                rows = result.mappings().all()

                for row in rows:
                    payload = {
                        "signal_id": row["id"],
                        "asset_id": row["asset_id"],
                        "ticker": row["ticker"],
                        "signal_type": row["signal_type"],
                        "direction": row["direction"],
                        "strength": row["strength"],
                        "confidence_tier": row["confidence_tier"],
                        "trigger_price": row["trigger_price"],
                    }

                    # Publish to alpha channel
                    if realtime_manager.has_subscribers("signals:alpha"):
                        await realtime_manager.publish(
                            "signals:alpha", "signal_alert", payload
                        )

                    # Publish to asset-specific signals channel
                    asset_ch = f"asset:{row['asset_id']}:signals"
                    if realtime_manager.has_subscribers(asset_ch):
                        await realtime_manager.publish(
                            asset_ch, "signal_alert", payload
                        )

                if rows:
                    self._last_signal_at = rows[0]["detected_at"]
                break

        except Exception as e:
            logger.warning("poller.signals_query_failed", error=str(e))

    async def _poll_sessions(self, channels: list[str]) -> None:
        """Fetch session status changes and publish to subscribers."""
        try:
            from sqlalchemy import text

            async for db in get_db():
                since = self._last_session_at or datetime.now(timezone.utc)
                result = await db.execute(
                    text("""
                        SELECT s.id, s.asset_id, s.session_date, s.status,
                               s.open_price, s.close_price, s.change_pct,
                               s.updated_at, ac.code as asset_class
                        FROM fin_sessions s
                        JOIN fin_assets a ON a.id = s.asset_id
                        JOIN fin_asset_classes ac ON ac.id = a.asset_class_id
                        WHERE s.updated_at > :since
                        ORDER BY s.updated_at DESC
                        LIMIT 50
                    """),
                    {"since": since},
                )
                rows = result.mappings().all()

                for row in rows:
                    session_date = str(row["session_date"])
                    channel = f"sessions:{row['asset_class']}:{session_date}"
                    if realtime_manager.has_subscribers(channel):
                        await realtime_manager.publish(
                            channel,
                            "session_update",
                            {
                                "session_id": row["id"],
                                "asset_id": row["asset_id"],
                                "status": row["status"],
                                "open_price": row["open_price"],
                                "close_price": row["close_price"],
                                "change_pct": row["change_pct"],
                            },
                        )

                if rows:
                    self._last_session_at = rows[0]["updated_at"]
                break

        except Exception as e:
            logger.warning("poller.sessions_query_failed", error=str(e))


# ── Singleton ───────────────────────────────────────────────────────────────

db_poller = DBPoller()
