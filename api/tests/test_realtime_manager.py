"""Tests for the realtime connection manager."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.realtime.manager import (
    RealtimeManager,
    SSEConnection,
    WSConnection,
    MAX_CHANNELS_PER_CONNECTION,
)


class MockConnection:
    """Simple mock connection for testing."""

    def __init__(self, conn_id: str = "test-1"):
        self._id = conn_id
        self.sent: list[str] = []

    @property
    def id(self) -> str:
        return self._id

    async def send_event(self, data: str) -> None:
        self.sent.append(data)


class FailingConnection:
    """Connection that always fails on send."""

    def __init__(self, conn_id: str = "fail-1"):
        self._id = conn_id

    @property
    def id(self) -> str:
        return self._id

    async def send_event(self, data: str) -> None:
        raise ConnectionError("send failed")


class TestRealtimeManager:
    def test_subscribe(self):
        mgr = RealtimeManager()
        conn = MockConnection()
        assert mgr.subscribe(conn, "prices:CRYPTO") is True
        assert mgr.has_subscribers("prices:CRYPTO") is True

    def test_subscribe_limit(self):
        mgr = RealtimeManager()
        conn = MockConnection()
        for i in range(MAX_CHANNELS_PER_CONNECTION):
            mgr.subscribe(conn, f"asset:{i}:price")
        # One more should fail
        assert mgr.subscribe(conn, "prices:CRYPTO") is False

    def test_unsubscribe(self):
        mgr = RealtimeManager()
        conn = MockConnection()
        mgr.subscribe(conn, "prices:CRYPTO")
        mgr.unsubscribe(conn, "prices:CRYPTO")
        assert mgr.has_subscribers("prices:CRYPTO") is False

    def test_disconnect_clears_all(self):
        mgr = RealtimeManager()
        conn = MockConnection()
        mgr.subscribe(conn, "prices:CRYPTO")
        mgr.subscribe(conn, "prices:STOCKS")
        mgr.disconnect(conn)
        assert mgr.has_subscribers("prices:CRYPTO") is False
        assert mgr.has_subscribers("prices:STOCKS") is False

    def test_active_channels(self):
        mgr = RealtimeManager()
        c1 = MockConnection("c1")
        c2 = MockConnection("c2")
        mgr.subscribe(c1, "prices:CRYPTO")
        mgr.subscribe(c2, "signals:alpha")
        assert mgr.active_channels() == {"prices:CRYPTO", "signals:alpha"}

    @pytest.mark.asyncio
    async def test_publish_sends_to_subscribers(self):
        mgr = RealtimeManager()
        c1 = MockConnection("c1")
        c2 = MockConnection("c2")
        c3 = MockConnection("c3")  # Not subscribed to this channel

        mgr.subscribe(c1, "prices:CRYPTO")
        mgr.subscribe(c2, "prices:CRYPTO")
        mgr.subscribe(c3, "prices:STOCKS")

        sent = await mgr.publish("prices:CRYPTO", "price_update", {"price": 50000})
        assert sent == 2
        assert len(c1.sent) == 1
        assert len(c2.sent) == 1
        assert len(c3.sent) == 0

    @pytest.mark.asyncio
    async def test_publish_to_empty_channel(self):
        mgr = RealtimeManager()
        sent = await mgr.publish("prices:CRYPTO", "price_update", {"price": 50000})
        assert sent == 0

    @pytest.mark.asyncio
    async def test_publish_removes_dead_connections(self):
        mgr = RealtimeManager()
        good = MockConnection("good")
        bad = FailingConnection("bad")

        mgr.subscribe(good, "prices:CRYPTO")
        mgr.subscribe(bad, "prices:CRYPTO")

        sent = await mgr.publish("prices:CRYPTO", "price_update", {"price": 50000})
        assert sent == 1
        # Bad connection should be cleaned up
        assert mgr.status()["total_connections"] == 1

    @pytest.mark.asyncio
    async def test_sequence_tracking(self):
        mgr = RealtimeManager()
        conn = MockConnection()
        mgr.subscribe(conn, "prices:CRYPTO")

        await mgr.publish("prices:CRYPTO", "price_update", {"p": 1})
        await mgr.publish("prices:CRYPTO", "price_update", {"p": 2})

        import json
        e1 = json.loads(conn.sent[0])
        e2 = json.loads(conn.sent[1])
        assert e1["seq"] == 1
        assert e2["seq"] == 2

    def test_status(self):
        mgr = RealtimeManager()
        c1 = MockConnection("c1")
        mgr.subscribe(c1, "prices:CRYPTO")
        mgr.subscribe(c1, "signals:alpha")

        status = mgr.status()
        assert status["total_connections"] == 1
        assert status["total_channels"] == 2
        assert status["channels"]["prices:CRYPTO"] == 1
        assert status["channels"]["signals:alpha"] == 1
        assert status["publish_count"] == 0
        assert "boot_epoch" in status

    @pytest.mark.asyncio
    async def test_first_subscriber_callback(self):
        mgr = RealtimeManager()
        callback_channels = []

        async def on_first(channel: str):
            callback_channels.append(channel)

        mgr.set_on_first_subscriber(on_first)

        conn = MockConnection()
        mgr.subscribe(conn, "prices:CRYPTO")

        # Let the callback task run
        await asyncio.sleep(0.01)
        assert "prices:CRYPTO" in callback_channels

    @pytest.mark.asyncio
    async def test_no_callback_on_second_subscriber(self):
        mgr = RealtimeManager()
        callback_channels = []

        async def on_first(channel: str):
            callback_channels.append(channel)

        mgr.set_on_first_subscriber(on_first)

        c1 = MockConnection("c1")
        c2 = MockConnection("c2")
        mgr.subscribe(c1, "prices:CRYPTO")
        mgr.subscribe(c2, "prices:CRYPTO")

        await asyncio.sleep(0.01)
        # Should only fire once
        assert callback_channels.count("prices:CRYPTO") == 1

    def test_multiple_connections_same_channel(self):
        mgr = RealtimeManager()
        conns = [MockConnection(f"c{i}") for i in range(5)]
        for c in conns:
            mgr.subscribe(c, "prices:CRYPTO")

        assert mgr.status()["channels"]["prices:CRYPTO"] == 5
        assert mgr.status()["total_connections"] == 5


class TestSSEConnection:
    @pytest.mark.asyncio
    async def test_send_event(self):
        conn = SSEConnection()
        await conn.send_event("test data")
        assert conn.queue.qsize() == 1
        data = await conn.queue.get()
        assert data == "test data"

    @pytest.mark.asyncio
    async def test_queue_overflow(self):
        conn = SSEConnection()
        # Fill the queue
        for i in range(200):
            await conn.send_event(f"data-{i}")
        # Next should raise
        with pytest.raises(ConnectionError):
            await conn.send_event("overflow")

    def test_unique_id(self):
        c1 = SSEConnection()
        c2 = SSEConnection()
        assert c1.id != c2.id
        assert c1.id.startswith("sse-")


class TestWSConnection:
    @pytest.mark.asyncio
    async def test_send_event(self):
        mock_ws = AsyncMock()
        conn = WSConnection(mock_ws)
        await conn.send_event("test data")
        mock_ws.send_text.assert_called_once_with("test data")

    def test_unique_id(self):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        c1 = WSConnection(ws1)
        c2 = WSConnection(ws2)
        assert c1.id != c2.id
        assert c1.id.startswith("ws-")
