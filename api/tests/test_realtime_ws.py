"""Tests for WebSocket endpoint logic."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.realtime.ws import _ping_loop


class TestPingLoop:
    @pytest.mark.asyncio
    async def test_ping_sends_json(self):
        ws = AsyncMock()
        ws.send_json = AsyncMock()

        import asyncio

        async def run_briefly():
            task = asyncio.create_task(_ping_loop(ws, "test-conn"))
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        with patch("app.realtime.ws.WS_PING_INTERVAL_S", 0.01):
            await run_briefly()

        # Should have sent at least one ping
        assert ws.send_json.call_count >= 1
        ws.send_json.assert_called_with({"type": "ping"})

    @pytest.mark.asyncio
    async def test_ping_stops_on_send_error(self):
        ws = AsyncMock()
        ws.send_json = AsyncMock(side_effect=Exception("connection closed"))

        import asyncio

        with patch("app.realtime.ws.WS_PING_INTERVAL_S", 0.01):
            task = asyncio.create_task(_ping_loop(ws, "test-conn"))
            await asyncio.sleep(0.05)
            # Task should have exited due to send error
            assert task.done() or task.cancelled()
            if not task.done():
                task.cancel()

    @pytest.mark.asyncio
    async def test_ping_handles_cancellation(self):
        ws = AsyncMock()
        ws.send_json = AsyncMock()

        import asyncio

        with patch("app.realtime.ws.WS_PING_INTERVAL_S", 10):  # Long interval
            task = asyncio.create_task(_ping_loop(ws, "test-conn"))
            await asyncio.sleep(0.01)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            assert task.done()
